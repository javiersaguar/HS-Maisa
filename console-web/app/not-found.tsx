import Link from 'next/link'
import { FileQuestion } from 'lucide-react'
import { BRAND } from '@/lib/config'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/states'

export default function NotFound() {
  return (
    <div className="mx-auto max-w-[720px] p-6 pt-16">
      <title>{`Página no encontrada · ${BRAND}`}</title>
      <Card>
        <EmptyState
          icon={<FileQuestion className="size-5" />}
          title="Esta página no existe"
          description="Puede que el enlace esté desactualizado. Vuelve al panel para seguir."
          action={
            <Link href="/" className="bg-accent-dark px-4 py-2 text-[14px] font-semibold text-canvas hover:bg-accent-dark">
              Volver al panel
            </Link>
          }
        />
      </Card>
    </div>
  )
}
