export default function Header({ data, geradoEm }) {
  const dataFormatada = data
    ? new Date(data + "T12:00:00").toLocaleDateString("pt-BR", {
        weekday: "long", day: "2-digit", month: "long", year: "numeric"
      })
    : null

  const horaGeracao = geradoEm
    ? new Date(geradoEm).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    : null

  return (
    <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-lg">
            ⚽
          </div>
          <div>
            <h1 className="text-white font-bold text-base leading-tight">
              Lay Goleada & Lay 0x0
            </h1>
            <p className="text-slate-500 text-xs">IA para mercados esportivos</p>
          </div>
        </div>

        {dataFormatada && (
          <div className="text-right">
            <p className="text-slate-300 text-sm font-medium capitalize">{dataFormatada}</p>
            {horaGeracao && (
              <p className="text-slate-600 text-xs">Gerado às {horaGeracao}</p>
            )}
          </div>
        )}
      </div>
    </header>
  )
}
