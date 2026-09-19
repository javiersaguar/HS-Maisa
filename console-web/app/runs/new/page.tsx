import { FuncionCongelada } from '@/components/layout/FuncionCongelada'

export default function NewRunPage() {
  return (
    <FuncionCongelada
      titulo="El pipeline se lanza con albertitos run"
      descripcion="La consola es de sólo lectura. Para procesar la Caja o un lote nuevo, ejecuta albertitos run (o make run) en el repo de HS-Maisa; los resultados aparecen aquí."
    />
  )
}
