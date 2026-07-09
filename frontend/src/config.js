// Base URL dell'API Flask, unico punto di configurazione per tutto il frontend.
// - In sviluppo (npm run dev) punta al server Flask locale sulla porta 5001.
// - In produzione usa URL relativi ('') così le chiamate /api/* passano da nginx,
//   che fa da reverse proxy verso il backend sulla stessa macchina (niente CORS,
//   niente porta 5001 esposta).
// - VITE_API_URL, se definita al momento della build, ha la precedenza su tutto.
export const API_URL =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:5001' : '')
