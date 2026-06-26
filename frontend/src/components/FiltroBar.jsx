const FILTROS = [
  { value: "TODOS", label: "Todos" },
  { value: "ENTRAR", label: "✅ Entrar" },
  { value: "LAY_GOLEADA", label: "⚽ Lay Goleada" },
  { value: "LAY_0X0", label: "0️⃣ Lay 0x0" },
]

export default function FiltroBar({ filtro, onChange }) {
  return (
    <div className="flex gap-2 flex-wrap">
      {FILTROS.map(f => (
        <button
          key={f.value}
          onClick={() => onChange(f.value)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-all border ${
            filtro === f.value
              ? "bg-emerald-500 text-white border-emerald-500"
              : "bg-slate-800/60 text-slate-400 border-slate-700 hover:border-slate-500"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  )
}
