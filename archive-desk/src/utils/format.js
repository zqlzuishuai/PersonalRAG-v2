/** utils/format.js —— 时间戳与编号的统一格式（全站等宽数字） */

const pad = (n) => String(n).padStart(2, '0')

export const hms = (d = new Date()) => `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`

export const hm = (d = new Date()) => `${pad(d.getHours())}:${pad(d.getMinutes())}`

export const ymd = (d = new Date()) => `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`

export const dayName = (d = new Date()) =>
  ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'][d.getDay()]

export const fullDate = (d = new Date()) =>
  `${dayName(d)} · ${pad(d.getDate())} ${['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'][d.getMonth()]} ${d.getFullYear()}`

export const pad4 = (s) => (s || '').toString().slice(0, 4).toUpperCase().padEnd(4, ' ')
