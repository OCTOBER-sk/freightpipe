import { apiPost, apiGet, apiPut } from "./client";

export interface RegisterRequest {
  email: string;
  phone?: string;
  company_name: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  token: string;
  user: UserProfile;
}

export interface UserProfile {
  id: string;
  email: string;
  phone: string | null;
  company_name: string;
  created_at: string;
}

export interface UpdateProfileRequest {
  email?: string;
  phone?: string;
  company_name?: string;
}

export function register(data: RegisterRequest): Promise<AuthResponse> {
  return apiPost<AuthResponse>("/auth/register", data);
}

export function login(data: LoginRequest): Promise<AuthResponse> {
  return apiPost<AuthResponse>("/auth/login", data);
}

export function getProfile(): Promise<UserProfile> {
  return apiGet<UserProfile>("/auth/me");
}

export function updateProfile(data: UpdateProfileRequest): Promise<UserProfile> {
  return apiPut<UserProfile>("/auth/profile", data);
}
