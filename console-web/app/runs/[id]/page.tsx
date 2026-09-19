import { FuncionCongelada } from '@/components/layout/FuncionCongelada'

export default function RunPage() {
  return (
    <FuncionCongelada
      titulo="El pipeline se lanza con albertitos run"
      descripcion="Esta consola no sigue ejecuciones. Cada etapa deja eventos en la base de datos: consúltalos en Etapas o en Traza."
    />
  )
}
