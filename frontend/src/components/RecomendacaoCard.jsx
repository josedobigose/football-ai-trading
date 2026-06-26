export default function RecomendacaoCard({ rec }) {
  const isEntrar = rec.status === "ENTRAR"
  const is0x0 = rec.mercado === "LAY_0X0"
  const isNaoOperar = rec.mercado === "NAO_OPERAR"

  const mercadoLabel = () => {
    if (isNaoOperar) return "NÃO OPERAR"
    if (is0x0) return "LAY 0x0"
    return `LAY GOLEADA — ${rec.lado === "CASA" ? "TIME DA CASA" : "TIME VISITANTE"}`
  }

  const iqColor = () => {
    if (rec.indice_qualidade >= 95) return "text-emerald-400"
    if (rec.indice_qualidade >= 90) return "text-green-400"
    if (rec.indice_qualidade >= 80) return "text-yellow-400"
    return "text-red-400"
  }

  const riscoColor = () => {
    if (rec.risco === "BAIXO") return "bg-emerald-900/50 text-emerald-400 border-emerald-800"
    if (rec.risco === "MEDIO") return "bg-yellow-900/50 text-yellow-400 border-yellow-800"
    return "bg-red-900/50 text-red-400 border-red-800"
  }

  const horario = rec.horario
    ? new Date(rec.horario).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : "--:--"

  return (
    <div className={`rounded-2xl border p-5 transition-all ${
      isEntrar
        ? "bg-slate-800/60 border-slate-700 hover:border-emerald-700"
        : "bg-slate-900/40 border-slate-800 opacity-60"
    }`}>
      {/* Header do card */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">
            {rec.campeonato}
          </p>
          <h2 className="text-white font-bold text-lg leading-tight">
            {rec.jogo}
          </h2>
          <p className="text-slate-400 text-sm mt-0.5">🕐 {horario}</p>
        </div>

        <div className="text-right shrink-0">
          <span className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${
            isEntrar
              ? "bg-emerald-900/50 text-emerald-400 border-emerald-700"
              : "bg-slate-800 text-slate-500 border-slate-700"
          }`}>
            {isEntrar ? "✅ ENTRAR" : "⏭️ NÃO OPERAR"}
          </span>
        </div>
      </div>

      {/* Mercado */}
      {!isNaoOperar && (
        <div className="mt-4 bg-slate-900/60 rounded-xl p-3 border border-slate-700/50">
          <p className="text-xs text-slate-500 mb-0.5">Mercado</p>
          <p className="text-emerald-400 font-bold text-sm tracking-wide">
            {mercadoLabel()}
          </p>
          {is0x0 && (
            <p className="text-yellow-500 text-xs mt-1">
              ⚠️ Fechar obrigatoriamente aos 65 min se 0x0
            </p>
          )}
        </div>
      )}

      {/* Métricas */}
      {!isNaoOperar && (
        <div className="grid grid-cols-3 gap-3 mt-4">
          <div className="bg-slate-900/60 rounded-xl p-3 text-center">
            <p className="text-xs text-slate-500 mb-1">Probabilidade</p>
            <p className="text-white font-bold text-xl">{rec.probabilidade}%</p>
          </div>
          <div className="bg-slate-900/60 rounded-xl p-3 text-center">
            <p className="text-xs text-slate-500 mb-1">Índice Qualidade</p>
            <p className={`font-bold text-xl ${iqColor()}`}>{rec.indice_qualidade}</p>
          </div>
          <div className="bg-slate-900/60 rounded-xl p-3 text-center">
            <p className="text-xs text-slate-500 mb-1">Risco</p>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${riscoColor()}`}>
              {rec.risco}
            </span>
          </div>
        </div>
      )}

      {/* Justificativas */}
      {rec.justificativas?.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Justificativas</p>
          <ul className="space-y-1">
            {rec.justificativas.map((j, i) => (
              <li key={i} className="text-slate-300 text-sm flex gap-2">
                <span className="text-slate-600 mt-0.5">→</span>
                <span>{j}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
