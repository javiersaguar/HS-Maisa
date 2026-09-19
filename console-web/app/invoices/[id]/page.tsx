import { redirect } from 'next/navigation'
import { ficheroHref } from '@/lib/routes'

/**
 * Alias de las URLs viejas (`/invoices/scan_017.pdf`, las del guion): el detalle vive en
 * `/invoices/detalle?file=` (ver lib/routes.ts). Next puede entregar el segmento aún codificado,
 * así que se decodifica mientras quede un `%XX`.
 */
function fileIdFrom(segmento: string): string {
  let valor = segmento
  for (let i = 0; i < 3 && /%[0-9A-Fa-f]{2}/.test(valor); i++) {
    try {
      valor = decodeURIComponent(valor)
    } catch {
      break
    }
  }
  return valor.normalize('NFC')
}

export default async function FicheroAlias({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  redirect(ficheroHref(fileIdFrom(id)))
}
