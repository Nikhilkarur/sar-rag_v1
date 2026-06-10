import client from './client'
import type { User } from '../types'

export async function login(payload: any): Promise<{ access_token: string; refresh_token: string; user: User }> {
  const { data } = await client.post('/auth/login', payload)
  return data
}

export async function signup(payload: any): Promise<{ access_token: string; refresh_token: string; user: User }> {
  const { data } = await client.post('/auth/signup', payload)
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await client.get('/auth/me')
  return data
}
