// server side
import Credentials from "next-auth/providers/credentials"
import type { Provider } from "next-auth/providers"
import type { NextAuthConfig } from 'next-auth';

const providers: Provider[] = [
    Credentials({
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' }
      },
      authorize: async (credentials) => {
        console.log("authorize")

        if (!credentials?.email || !credentials?.password) {
          return null
        }
        console.log(credentials?.email, credentials?.password)
        // Type assertion to ensure credentials are strings
        const email = credentials.email as string
        const password = credentials.password as string

        const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
        const reqBody = new URLSearchParams({
          email,
          password,
        });

        try {
          const response = await fetch(`${backendUrl}/token/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: reqBody,
          });
          console.log(response)
          if (!response.ok) {
            console.error("user not found")
            return null
          }

          const data = await response.json();
          const user = data?.user;
          if (!user?.email) {
            return null
          }

          return {
            id: user.id,
            email: user.email,
            name: user.name || ''
          };
        } catch (err) {
          console.error("authorize error", err)
          return null
        }
      }
    })
  ]

export const providerMap = providers.map((provider) => {
	if (typeof provider === "function") {
		const providerData = provider()
		console.log("1", providerData.id, providerData.name)
		return { id: providerData.id, name: providerData.name }
	} else {
		console.log("2", provider.id, provider.name)
		return { id: provider.id, name: provider.name }
	}
})

export const authConfig = {
  pages: {
    signIn: '/signin',
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      return true;
    },   
  },
  providers: providers,
} satisfies NextAuthConfig;
