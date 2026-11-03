import type { Metadata, Viewport } from 'next'
import './globals.css'
import { THEME_SCRIPT } from '@/lib/theme'

export const metadata: Metadata = {
  title: 'Kairos — Seguimiento de proyectos',
  description: 'Registra ideas y decisiones, mide el avance real y no abandones tus proyectos.',
  icons: {
    icon: '/icon.svg',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' },
  ],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="antialiased">
        {children}
      </body>
    </html>
  )
}
