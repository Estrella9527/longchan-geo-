"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import type { UserInfo } from "@/types";

export function useAuth() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        setLoading(false);
        return;
      }
      const res = await api.get<UserInfo>("/auth/me");
      setUser(res.data);
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = async (username: string, password: string) => {
    const res = await api.post("/auth/login", { username, password });
    localStorage.setItem("access_token", res.data.access_token);
    localStorage.setItem("refresh_token", res.data.refresh_token);
    await fetchUser();
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
    router.push("/login");
  };

  return { user, loading, login, logout };
}
