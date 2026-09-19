import Link from 'next/link'
import { Terminal } from 'lucide-react'
import { BRAND } from '@/lib/config'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/states'

/**
 * Lo que ve quien entra por URL a una pantalla del prototipo que Albertitos no tiene
 * (PLAN-ADAPTACION.md §1.4). El código original está en `congelado/`.
 */
export function FuncionCongelada({ titulo, descripcion }: { titulo: string; descripcion: string }) {
  return (
    <div className="mx-auto max-w-[720px] p-6 pt-16">
      <title>{`${titulo} · ${BRAND}`}</title>
      <Card>
        <EmptyState
          icon={<Terminal className="size-5" />}
          title={titulo}
          description={descripcion}
          action={
            <Link href="/" className="rounded-lg bg-[#164f45] px-4 py-2 text-[14px] font-semibold text-white hover:bg-[#0d4037]">
              Volver al panel
            </Link>
          }
        />
      </Card>
    </div>
  )
}
