import { useState, useEffect } from "react"
import RecomendacaoCard from "./components/RecomendacaoCard"
import Header from "./components/Header"
import FiltroBar from "./components/FiltroBar"
import Resumo from "./components/Resumo"

const BASE_URL = import.meta.env.VITE_BASE_URL || ""

export default function App() {
  const [dados, setDados] = useState(null)
  const [filtro, setFiltro] = useState("TODOS") // TODOS | ENTRAR | LAY_GOLEADA | LAY_0X0
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    const hoje = new Date().toISOString().split("T")[0]
    fetch(`${BASE_URL}/data/recomendacoes_${hoje}.json`)
      .then(r => {
        if (!r.ok) throw new Error("Análise do dia ainda não disponível.")
        return r.json()
      })
      .then(d => { setDados(d); setLoading(false) })
      .catch(e => { setErro(e.message); setLoading(false) })
  }, [])

  const recomendacoesFiltradas = dados?.recomendacoes?.filter(r => {
    if (filtro === "ENTRAR") return r.status === "ENTRAR"
    if (filtro === "LAY_GOLEADA") return r.mercado === "LAY_GOLEADA"
    if (filtro === "LAY_0X0") return r.mercado === "LAY_0X0"
    return true
  }) ?? []

  return (
    <div className="min-h-screen bg-[#0a0f1e] text-white font-sans">
      <Header data={dados?.data} geradoEm={dados?.gerado_em} />

      <main className="max-w-5xl mx-auto px-4 py-8">
        {loading && (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-slate-400">Carregando análise do dia...</p>
            </div>
          </div>
        )}

        {erro && (
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-8 text-center mt-8">
            <p className="text-4xl mb-4">⏳</p>
            <p className="text-slate-300 text-lg font-medium">{erro}</p>
            <p className="text-slate-500 text-sm mt-2">
              A análise é gerada automaticamente às 8h. Volte mais tarde.
            </p>
          </div>
        )}

        {dados && !loading && (
          <>
            <Resumo
              total={dados.total}
              entrar={dados.entrar}
              data={dados.data}
            />

            <FiltroBar filtro={filtro} onChange={setFiltro} />

            <div className="space-y-4 mt-6">
              {recomendacoesFiltradas.length === 0 ? (
                <div className="text-center text-slate-500 py-12">
                  Nenhuma recomendação nesse filtro.
                </div>
              ) : (
                recomendacoesFiltradas.map((rec, i) => (
                  <RecomendacaoCard key={i} rec={rec} />
                ))
              )}
            </div>
          </>
        )}
      </main>

      <footer className="text-center text-slate-600 text-xs py-8 mt-8 border-t border-slate-800">
        ⚠️ Recomendações probabilísticas — não garantem resultado.
        Use com responsabilidade.
      </footer>
    </div>
  )
}
