/**
 * Enlace al detalle de un fichero. El `file_id` va en la query, no en el path: Next recodifica los
 * segmentos dinámicos con tildes (`%C3%A1` → `%25C3%25A1`) y `next dev` los manda a 404
 * (next.js#73965). En la query viaja una sola vez codificado y `useSearchParams` lo devuelve limpio.
 */
export const ficheroHref = (fileId: string) =>
  `/invoices/detalle?file=${encodeURIComponent(fileId.normalize('NFC'))}`
