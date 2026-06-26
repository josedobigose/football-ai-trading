export function Resumo({ total, entrar, data }) {
  const naoOperar = total - entrar

  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-4 text-center">
        <p className="text-3xl font-bold text-white">{total}</p>
        <p className="text-slate-400 text-xs mt-1 uppercase tracking-wider">Jogos analisados</p>
      </div>
      <div className="bg-emerald-900/30 border border-emerald-800/50 rounded-2xl p-4 text-center">
        <p className="text-3xl font-bold text-emerald-400">{entrar}</p>
        <p className="text-emerald-600 text-xs mt-1 uppercase tracking-wider">Recomendados</p>
      </div>
      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 text-center">
        <p className="text-3xl font-bold text-slate-500">{naoOperar}</p>
        <p className="text-slate-600 text-xs mt-1 uppercase tracking-wider">Não operar</p>
      </div>
    </div>
  )
}

export default Resumo
