/**
 * data/registry.js
 * 内容层的唯一数据源：机构槽位、四阶段、签发凭据、档案登记簿。
 * 风格层只决定「长什么样」，这里只决定「说什么」。
 */

/* 槽位表 ------------------------------------------------------ */
export const org = {
  zh: '恒序档案署',
  en: 'PERPETUAL',
  en2: 'SYNTHESIS OF RECORDS',
  en3: 'ARCHIVAL DESK',
  mark: '∞', // 一笔可描的几何符号
  code: 'PR∞A', // 4 字符短代码，符号压第三位
  desk: 'EST. 1911',
}

/* 四阶段：竖轴标记块的 4 个档位 ------------------------------- */
export const stages = [
  { n: '01', en: 'RETRIEVE', zh: '检索', hint: '按类别与状态筛选登记簿' },
  { n: '02', en: 'VERIFY', zh: '核验', hint: '比对凭据等级与卷宗密级' },
  { n: '03', en: 'CONSULT', zh: '调阅', hint: '在阅览室原位查阅，不出库' },
  { n: '04', en: 'RESEAL', zh: '归档', hint: '归还、复核、重新封存' },
]

/* 已签发凭据：门禁处可点选填入 ------------------------------- */
export const credentials = [
  { code: 'K41M', holder: '调阅员 · 07', level: 'A', issued: '2026-10-02' },
  { code: '7VD2', holder: '调阅员 · 12', level: 'B', issued: '2026-10-11' },
  { code: 'W03R', holder: '值守 · 03', level: 'A', issued: '2026-09-28' },
]

export const classes = [
  { key: 'ALL', zh: '全部', en: 'ALL' },
  { key: '器物', zh: '器物', en: 'OBJECT' },
  { key: '文书', zh: '文书', en: 'DOCUMENT' },
  { key: '声像', zh: '声像', en: 'AUDIO' },
  { key: '地形', zh: '地形', en: 'TERRAIN' },
]

export const statuses = [
  { key: 'ALL', zh: '全部', en: 'ALL' },
  { key: 'OPEN', zh: '可调阅', en: 'OPEN' },
  { key: 'SEALED', zh: '封存', en: 'SEALED' },
  { key: 'RESTRICTED', zh: '限阅', en: 'RESTRICTED' },
]

/* 登记簿 ------------------------------------------------------ */
export const records = [
  {
    id: 'A-0317',
    zh: '沿海雾钟',
    en: 'COASTAL FOG BELL',
    cls: '器物',
    clsEn: 'OBJECT',
    status: 'SEALED',
    shelf: 'Ⅳ-22',
    year: '1947',
    unit: '1 件 · 高 42cm',
    abstract:
      '钟体铜铸，外壁盐蚀成片，内壁刻编号 317 与年份 1947。原悬于灯塔西南支柱，1961 年拆卸入档，随件附四页测音记录。',
    fields: [
      { k: 'OBJECT', v: '铜铸雾钟' },
      { k: 'ORIGIN', v: '灯塔西南支柱' },
      { k: 'ACCESSION', v: '1961-04-18' },
      { k: 'SHELF', v: 'Ⅳ-22' },
      { k: 'STATUS', v: 'SEALED' },
    ],
    log: [
      '1961-04-18 拆卸入档，编号 0317',
      '1978-11-02 内壁除盐，未取样',
      '2004-06-30 测音记录补录至附卷',
    ],
  },
  {
    id: 'A-0284',
    zh: '盐井测绘图',
    en: 'SALT WELL SURVEY',
    cls: '地形',
    clsEn: 'TERRAIN',
    status: 'OPEN',
    shelf: 'Ⅱ-09',
    year: '1953',
    unit: '1 幅 · 68×92cm',
    abstract:
      '井场等高线手绘于硫酸纸上，标注七口卤井与两条输卤渠。图纸右下角有两次修订的签名与日期，第二处签名已褪至不可辨。',
    fields: [
      { k: 'OBJECT', v: '手绘测绘图' },
      { k: 'MEDIUM', v: '硫酸纸 · 墨线' },
      { k: 'ACCESSION', v: '1953-09-07' },
      { k: 'SHELF', v: 'Ⅱ-09' },
      { k: 'STATUS', v: 'OPEN' },
    ],
    log: ['1953-09-07 随勘探报告入档', '1991-03-14 低温除酸处理', '2019-08-21 高精扫描，出图 4 幅'],
  },
  {
    id: 'A-0302',
    zh: '无字邮包',
    en: 'UNMARKED PARCEL',
    cls: '文书',
    clsEn: 'DOCUMENT',
    status: 'RESTRICTED',
    shelf: 'Ⅶ-14',
    year: '1961',
    unit: '1 件 · 未开箱',
    abstract:
      '邮包外层牛皮纸完整，收寄两栏均未填写，邮戳可读至月份。内含物件未经开箱登记，按入档条例第十二条整件封存。',
    fields: [
      { k: 'OBJECT', v: '牛皮纸邮包' },
      { k: 'ORIGIN', v: '来源栏空白' },
      { k: 'ACCESSION', v: '1961-12-03' },
      { k: 'SHELF', v: 'Ⅶ-14' },
      { k: 'STATUS', v: 'RESTRICTED' },
    ],
    log: ['1961-12-03 整件入档，未开箱', '1985-02-11 密级复核，维持原级', '2011-07-19 封条更换一次'],
  },
  {
    id: 'A-0119',
    zh: '雨声母带',
    en: 'RAIN MASTER TAPE',
    cls: '声像',
    clsEn: 'AUDIO',
    status: 'OPEN',
    shelf: 'Ⅰ-03',
    year: '1972',
    unit: '1 卷 · ¼ 英寸',
    abstract:
      '开盘母带一卷，标签手写「雨 · 六号院 · 夜」。带体有轻微霉斑，已转录一份供调阅，原件不再上机。',
    fields: [
      { k: 'OBJECT', v: '开盘母带' },
      { k: 'DURATION', v: '00:41:12' },
      { k: 'ACCESSION', v: '1972-05-26' },
      { k: 'SHELF', v: 'Ⅰ-03' },
      { k: 'STATUS', v: 'OPEN' },
    ],
    log: ['1972-05-26 随录音笔记入档', '1998-10-05 首次转录，磁带机 A-2', '2021-04-12 数码转录，24bit/96kHz'],
  },
  {
    id: 'A-0355',
    zh: '铜制罗盘残件',
    en: 'BRASS COMPASS, FRAGMENT',
    cls: '器物',
    clsEn: 'OBJECT',
    status: 'SEALED',
    shelf: 'Ⅳ-31',
    year: '1889',
    unit: '1 组 · 3 件',
    abstract:
      '盘面缺失，仅存黄铜壳体与一枚断裂的枢轴。壳内壁残留磁针磨痕，可推知原盘面直径约二十一厘米。',
    fields: [
      { k: 'OBJECT', v: '罗盘壳体 · 枢轴' },
      { k: 'MATERIAL', v: '黄铜 · 钢' },
      { k: 'ACCESSION', v: '1889-08-30' },
      { k: 'SHELF', v: 'Ⅳ-31' },
      { k: 'STATUS', v: 'SEALED' },
    ],
    log: ['1889-08-30 随船具清册入档', '1966-01-17 拆解登记，盘面判定缺失', '2015-09-09 X 射线荧光检测'],
  },
  {
    id: 'A-0421',
    zh: '搬迁名册',
    en: 'RELOCATION ROSTER',
    cls: '文书',
    clsEn: 'DOCUMENT',
    status: 'RESTRICTED',
    shelf: 'Ⅶ-02',
    year: '1984',
    unit: '1 册 · 14 页',
    abstract:
      '名册共十四页，记录迁出户主姓名、原址门牌与迁入编号。第六页起换用另一种墨水，字迹明显更为急促。',
    fields: [
      { k: 'OBJECT', v: '线装名册' },
      { k: 'PAGES', v: '14 / 14' },
      { k: 'ACCESSION', v: '1984-03-22' },
      { k: 'SHELF', v: 'Ⅶ-02' },
      { k: 'STATUS', v: 'RESTRICTED' },
    ],
    log: ['1984-03-22 由街道办移交', '1993-06-08 涉隐私条款，限制调阅', '2020-11-30 数字化，仅内网可见'],
  },
  {
    id: 'A-0093',
    zh: '潮位日志',
    en: 'TIDE LEDGER',
    cls: '文书',
    clsEn: 'DOCUMENT',
    status: 'OPEN',
    shelf: 'Ⅲ-07',
    year: '1928',
    unit: '1 册 · 连续四年',
    abstract:
      '逐日记录高低潮时刻与风级，连续四年零三个月。中间缺 1951 年 3 月共九天，缺页处有铅笔补记一行。',
    fields: [
      { k: 'OBJECT', v: '硬面日志簿' },
      { k: 'SPAN', v: '1928 – 1932' },
      { k: 'ACCESSION', v: '1932-07-01' },
      { k: 'SHELF', v: 'Ⅲ-07' },
      { k: 'STATUS', v: 'OPEN' },
    ],
    log: ['1932-07-01 观测站移交', '1975-04-23 缺页登记，9 日', '2018-02-06 录入潮位数据库'],
  },
  {
    id: 'A-0466',
    zh: '未冲洗底片',
    en: 'UNDEVELOPED PLATE',
    cls: '声像',
    clsEn: 'AUDIO',
    status: 'SEALED',
    shelf: 'Ⅰ-18',
    year: '1991',
    unit: '11 张 · 干板',
    abstract:
      '玻璃干板十一张，均未冲洗。外包装标注曝光日期与光圈值，其中三张的标注与内容不符，原因未明。',
    fields: [
      { k: 'OBJECT', v: '玻璃干板 11 张' },
      { k: 'FORMAT', v: '9×12cm' },
      { k: 'ACCESSION', v: '1991-10-15' },
      { k: 'SHELF', v: 'Ⅰ-18' },
      { k: 'STATUS', v: 'SEALED' },
    ],
    log: ['1991-10-15 整批入档，未冲洗', '2007-05-04 恒湿柜转移', '2022-01-20 抽样 2 张，均未显影'],
  },
  {
    id: 'A-0208',
    zh: '山脊界桩拓片',
    en: 'RIDGE MARKER RUBBING',
    cls: '地形',
    clsEn: 'TERRAIN',
    status: 'OPEN',
    shelf: 'Ⅱ-24',
    year: '1936',
    unit: '1 幅 · 双开',
    abstract:
      '界桩正面文字已风蚀，拓片取自背面编号与侧面刻痕。拓纸边缘有采集者铅笔注记，指明采集方位为北偏东十二度。',
    fields: [
      { k: 'OBJECT', v: '墨拓 · 宣纸' },
      { k: 'SITE', v: '北脊 04 号桩' },
      { k: 'ACCESSION', v: '1936-06-19' },
      { k: 'SHELF', v: 'Ⅱ-24' },
      { k: 'STATUS', v: 'OPEN' },
    ],
    log: ['1936-06-19 随测绘队报告入档', '1982-09-27 托裱修复', '2016-12-08 迁入恒湿库'],
  },
]

export const recordById = (id) => records.find((r) => r.id === id) || null

/* 日志流模板 -------------------------------------------------- */
export const streamLines = [
  'LEDGER SCAN OK',
  'SHELF MAPPING SYNC',
  'HUMIDITY 46% · STABLE',
  'SEAL INTEGRITY CHECK',
  'INDEX REBUILD · PARTIAL',
  'READER SLOT 02 ACTIVE',
  'REQUEST QUEUE EMPTY',
]
