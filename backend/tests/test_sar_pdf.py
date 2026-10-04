"""SAR PDF rendering — real status/approver, test marking, Unicode scripts, wrapping, determinism."""
import os
from types import SimpleNamespace

import pytest

from app.services import sar_pdf
from app.services.goaml_builder import build_goaml_str
from app.services.sar_pdf import render_sar_pdf

fitz = pytest.importorskip("fitz")  # pymupdf, used to read the rendered PDF back

HINDI = "राजेश कुमार शर्मा"
ARABIC = "شركة الأفق الخليجي"
APPROVED_AT = "2026-10-04T10:10:12.852256Z"
ALL_RULES = ["STRUCTURING", "RAPID_MOVEMENT", "ROUND_NUMBER", "HIGH_RISK_TYPE", "VELOCITY",
             "COUNTERPARTY_RISK", "RISK_SCORE_THRESHOLD"]


def _fixtures(status="APPROVED", synthetic=False, customer="Rohan Mehta", counterparty="Global Holdings"):
    alert = SimpleNamespace(
        status=status, risk_score=88, is_synthetic=synthetic,
        normalized_payload={
            "transaction_id": "TXN-1", "transaction_type": "INTERNATIONAL_WIRE",
            "customer_name": customer, "customer_id": "CUST-9007", "account_id": "9988-7766-5544",
            "counterparty_name": counterparty, "counterparty_institution": "Emirates NBD",
        },
        transaction_type="INTERNATIONAL_WIRE", transaction_amount=985000,
        transaction_currency="INR", transaction_id="TXN-1", transaction_timestamp=None,
    )
    draft = SimpleNamespace(
        id="68097d6d-0000-0000-0000-000000000001",
        draft_structured={"key_indicators": [{"indicator": "Structuring", "regulation": "PMLA",
                                              "description": f"Paid {counterparty}"}],
                          "recommended_action": "File the STR."},
        approved_text=f"{customer} wired INR 9,85,000 to {counterparty}.",
        rehydrated_text=None, draft_text="masked",
    )
    tenant = SimpleNamespace(tenant_id_public="TEN-0005", name="Meridian Bank Limited", id="uuid-1")
    return alert, draft, tenant


def _render(alert, draft, tenant, officer="Priya Nair", approved_at=APPROVED_AT, rules=ALL_RULES):
    goaml = build_goaml_str(alert, draft, rules, tenant, officer, approved_at)
    return render_sar_pdf(str(draft.id), alert, draft, goaml, officer, approved_at)


def _text(pdf: bytes) -> str:
    return "\n".join(page.get_text() for page in fitz.open(stream=pdf, filetype="pdf"))


def _fonts_in(pdf: bytes) -> set:
    return {f[3].split("+")[-1] for page in fitz.open(stream=pdf, filetype="pdf") for f in page.get_fonts()}


def _have_noto() -> bool:
    return all(s in sar_pdf._fonts() for s in ("latin", "deva", "arab"))


@pytest.fixture
def no_fonts(monkeypatch, tmp_path):
    """Pretend no Noto fonts are installed (Helvetica fallback)."""
    monkeypatch.setattr(sar_pdf, "_FONT_DIRS", [str(tmp_path)])
    sar_pdf._fonts.cache_clear()
    yield
    sar_pdf._fonts.cache_clear()


class TestStatusAndApprover:
    def test_approved_prints_real_approver_and_no_filing_claim(self):
        text = _text(_render(*_fixtures()))
        assert "APPROVED" in text
        assert f"Priya Nair - {APPROVED_AT}" in text
        assert "APPROVED & FILED" not in text
        assert "Filed to FIU-IND" not in text  # Aegis delivers to the bank; the bank files

    def test_unapproved_draft_has_no_approver(self):
        text = _text(_render(*_fixtures(status="PENDING_REVIEW")))
        assert "PENDING_REVIEW" in text
        assert "Approved By" not in text and "Priya Nair" not in text
        assert "Not approved; not for filing" in text

    def test_synthetic_alert_is_marked_test(self):
        text = _text(_render(*_fixtures(synthetic=True)))
        assert "TEST ALERT" in text and "APPROVED (TEST)" in text

    def test_render_is_deterministic(self):
        # The officer's re-rendered download must be byte-identical to the delivered copy.
        assert _render(*_fixtures()) == _render(*_fixtures())
        meta = fitz.open(stream=_render(*_fixtures()), filetype="pdf").metadata
        assert meta["creationDate"].startswith("D:20261004101012")


class TestDockerImageFonts:
    def test_font_dir_is_created_before_the_fonts_are_added(self):
        # ADD --chmod=644 into a missing directory creates it 644 (no x): the non-root app user
        # then cannot read the fonts and every PDF silently falls back to Helvetica.
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Dockerfile")
        if not os.path.exists(path):
            pytest.skip("Dockerfile not available")
        lines = open(path).read().splitlines()
        mkdir = next(i for i, l in enumerate(lines) if l.startswith("RUN mkdir -p /usr/share/fonts/truetype/noto"))
        adds = [i for i, l in enumerate(lines) if l.startswith("ADD ") and "Noto" in lines[i + 1]]
        assert len(adds) == 6 and mkdir < min(adds)


class TestLayout:
    def test_indicators_cell_wraps_instead_of_clipping(self):
        pdf = _render(*_fixtures())
        text = " ".join(_text(pdf).split())
        # every code is fully on the page (pdftotext used to show 'HIGH_COMPOSITE_RISK_SCO')
        assert "HIGH_COMPOSITE_RISK_SCORE" in text
        page = fitz.open(stream=pdf, filetype="pdf")[0]
        for word in page.get_text("words"):
            assert word[2] <= page.rect.width - 18 * 72 / 25.4 + 1, word  # inside the right margin

    def test_markup_characters_are_escaped(self):
        alert, draft, tenant = _fixtures(customer="A & B <Traders>")
        assert "A & B <Traders>" in _text(_render(alert, draft, tenant))


class TestUnicode:
    def test_rich_wraps_each_script_run_in_its_font(self, monkeypatch):
        monkeypatch.setattr(sar_pdf, "_fonts", lambda: {"deva": ("DevaR", "DevaB"), "arab": ("ArabR", "ArabB")})
        monkeypatch.setattr(sar_pdf, "_shape_arabic", lambda t: t)
        monkeypatch.setattr(sar_pdf, "_shape_devanagari", lambda t, font: t)
        out = sar_pdf._rich(f"{HINDI} / 9988 & {ARABIC} @ NBD")
        assert out == (f'<font name="DevaR">{HINDI} </font>/ 9988 &amp; '
                       f'<font name="ArabR">{ARABIC} </font>@ NBD')
        assert sar_pdf._rich(HINDI, bold=True) == f'<font name="DevaB">{HINDI}</font>'

    def test_missing_fonts_fall_back_without_crashing(self, no_fonts):
        assert sar_pdf._fonts() == {}
        assert sar_pdf._rich(HINDI) == HINDI
        pdf = _render(*_fixtures(customer=HINDI, counterparty=ARABIC))
        assert pdf.startswith(b"%PDF") and "Helvetica" in _fonts_in(pdf)

    @pytest.mark.skipif(not _have_noto(), reason="Noto fonts not installed (see backend/Dockerfile)")
    def test_devanagari_and_arabic_render_with_embedded_fonts(self):
        pdf = _render(*_fixtures(customer=HINDI, counterparty=ARABIC), officer="प्रिया नायर")
        fonts = _fonts_in(pdf)
        assert {"NotoSans-Regular", "NotoSansDevanagari-Regular", "NotoSansArabic-Regular"} <= fonts
        text = _text(pdf)
        # words without conjuncts extract as typed (shaped conjunct glyphs extract as private-use)
        assert "राजेश कुमार" in text and "नायर" in text
        assert "■" not in text
        # Arabic is shaped into joined presentation forms
        assert any(0xFE70 <= ord(c) <= 0xFEFF for c in text)

    @pytest.mark.skipif(not _have_noto() or sar_pdf.uharfbuzz is None, reason="needs Noto fonts + uharfbuzz")
    def test_devanagari_is_shaped(self):
        font = sar_pdf._fonts()["deva"][0]
        shaped = sar_pdf._shape_devanagari("किशोर", font)
        # the vowel sign i is drawn first (before क), as written — not 'कशिोर'
        assert shaped[1:] == "कशोर" and shaped[0] != "क"
        # reph and conjuncts are formed: no visible virama left
        for word in ("शर्मा", "प्रिया", "क्रिटिक"):
            assert "\u094D" not in sar_pdf._shape_devanagari(word, font), word
        # glyphs without a codepoint are drawn through U+E000 + glyph id
        face = sar_pdf.pdfmetrics.getFont(font).face
        pua = [c for c in sar_pdf._shape_devanagari("प्रिया", font) if 0xE000 <= ord(c) <= 0xF8FF]
        assert pua and all(face.charToGlyph[ord(c)] == ord(c) - 0xE000 for c in pua)

    @pytest.mark.skipif(not _have_noto() or sar_pdf.uharfbuzz is None, reason="needs Noto fonts + uharfbuzz")
    def test_shaped_render_does_not_depend_on_what_was_rendered_before(self):
        # the downloaded re-render (another process, other SARs rendered first) must still be
        # byte-identical to the delivered copy
        first = _render(*_fixtures(customer=HINDI, counterparty=ARABIC))
        _render(*_fixtures(customer="क्षत्रिय ज्ञानेश्वर द्विवेदी श्रीनिवास", counterparty=ARABIC))
        assert _render(*_fixtures(customer=HINDI, counterparty=ARABIC)) == first

    def test_without_shaper_vowel_sign_i_is_moved_before_its_consonant(self, monkeypatch):
        monkeypatch.setattr(sar_pdf, "uharfbuzz", None)
        assert sar_pdf._shape_devanagari("किशोर", "unused") == "िकशोर"
        assert sar_pdf._reorder_i_matra("प्रिया") == "िप्रया"  # whole conjunct cluster
        assert sar_pdf._reorder_i_matra("क्रिटिक") == "िक्रिटक"
        assert sar_pdf._reorder_i_matra("ज़ि") == "िज़"  # nukta stays with its consonant
        assert sar_pdf._reorder_i_matra(HINDI) == HINDI

    @pytest.mark.skipif(sar_pdf._bidi_display is None, reason="python-bidi not installed")
    def test_brackets_in_right_to_left_runs_are_mirrored(self):
        mirrored = sar_pdf._bidi_mirrored
        # an RTL pair is displayed with its glyphs swapped back: '(ش.م.ع)' not ')ع.م.ش('
        assert mirrored("مصرف (ش.م.ع)") == "(ع.م.ش) فرصم"
        # LTR pairs are left alone, even around or inside RTL text
        assert mirrored("x (مصرف) y") == "x (فرصم) y"
        assert mirrored("مصرف (abc) دبي") == "فرصم (abc) يبد"
        # an RTL pair nested in an LTR one (a naive bracket matcher pairs these wrongly)
        assert mirrored("Bank (abc مصرف (ش.م.ع) def) x") == "Bank (abc (ع.م.ش) فرصم def) x"
        assert mirrored("(مصرف [دبي] الوطني) ok") == "(ينطولا [يبد] فرصم) ok"

    @pytest.mark.skipif(sar_pdf.arabic_reshaper is None, reason="arabic-reshaper / python-bidi not installed")
    def test_arabic_is_reordered_for_display(self):
        shaped = sar_pdf._shape_arabic(f"To {ARABIC} @ NBD")
        assert shaped.startswith("To ") and shaped.endswith(" @ NBD")
        assert shaped != f"To {ARABIC} @ NBD"
        assert "ش" not in shaped  # isolated SHEEN replaced by its joined form
