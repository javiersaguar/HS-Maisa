import type { Metadata, Viewport } from 'next'
import { AppShell } from '@/components/layout/AppShell'
import { ChatPanel } from '@/components/chat/ChatPanel'
import './globals.css'

export const metadata: Metadata = {
  title: 'Albertitos · Cuentas a pagar',
  description: 'Consola de sólo lectura de Albertitos: ficheros, decisiones de la norma y traza de cada factura.',
  icons: {
    icon: [
      { url: '/logo-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/logo.png', sizes: '256x256', type: 'image/png' },
    ],
    apple: '/logo-apple.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light',
  themeColor: 'white',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="es">
      <body className="antialiased">
        <AppShell>{children}</AppShell>
        <ChatPanel />
      </body>
    </html>
  )
}
