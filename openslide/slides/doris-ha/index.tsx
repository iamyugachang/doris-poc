import type { ReactNode } from 'react';
import type { DesignSystem, Page, SlideMeta } from '@open-slide/core';
import { Step, Steps, useSlidePageNumber } from '@open-slide/core';

import archNormal from './assets/arch-normal.svg';
import archDown from './assets/arch-down.svg';
import flow from './assets/flow.svg';
import envState from './assets/env-state.svg';
import availState from './assets/avail-state.svg';
import timeline from './assets/timeline.svg';
import data from './data.json';

const FONT_HREF =
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@500;700&family=Noto+Sans+TC:wght@400;700&display=swap';
const FONT_LINK_ID = 'osd-webfont-doris-ha';
if (typeof document !== 'undefined' && !document.getElementById(FONT_LINK_ID)) {
  const link = document.createElement('link');
  link.id = FONT_LINK_ID;
  link.rel = 'stylesheet';
  link.href = FONT_HREF;
  document.head.appendChild(link);
}

export const design: DesignSystem = {
  palette: { bg: '#fffcf5', text: '#0f1a14', accent: '#11a679' },
  fonts: {
    display: '"JetBrains Mono", "Noto Sans TC", ui-monospace, Menlo, monospace',
    body: '"Inter", "Noto Sans TC", system-ui, -apple-system, sans-serif',
  },
  typeScale: { hero: 120, body: 36 },
  radius: 16,
};

const muted = '#4f5e56';
const soft = '#7f8f86';
const border = '#d9eee8';
const surface = '#f4fbf8';
const deep = '#0b7a58';
const yellow = '#ffd23f';
const yellowSoft = '#fff1c2';
const red = '#8a1f16';
const redSoft = '#ffe2dd';
const amberSoft = '#ffe8c2';
const amber = '#7a3e00';
const mono = '"JetBrains Mono", ui-monospace, Menlo, monospace';

const fill = {
  width: '100%',
  height: '100%',
  background: 'var(--osd-bg)',
  color: 'var(--osd-text)',
  fontFamily: 'var(--osd-font-body)',
  position: 'relative' as const,
  boxSizing: 'border-box' as const,
};

const Eyebrow = ({ children }: { children: string }) => (
  <div style={{ fontFamily: mono, fontSize: 24, fontWeight: 700, letterSpacing: '0.18em', color: deep, textTransform: 'uppercase' }}>
    {children}
  </div>
);

const Heading = ({ children }: { children: ReactNode }) => (
  <h2
    style={{
      fontFamily: 'var(--osd-font-display)',
      fontSize: 72,
      fontWeight: 800,
      lineHeight: 1.1,
      letterSpacing: '-0.03em',
      textTransform: 'uppercase',
      margin: '16px 0 0',
    }}
  >
    {children}
  </h2>
);

const Footer = () => {
  const { current, total } = useSlidePageNumber();
  return (
    <div
      style={{
        position: 'absolute',
        left: 120,
        right: 120,
        bottom: 48,
        display: 'flex',
        justifyContent: 'space-between',
        fontFamily: mono,
        fontSize: 22,
        color: soft,
        letterSpacing: '0.08em',
      }}
    >
      <span>APACHE DORIS · HA POC · GCP ASIA-EAST1</span>
      <span>
        {String(current).padStart(2, '0')} / {String(total).padStart(2, '0')}
      </span>
    </div>
  );
};

const Level = ({ kind, children, small = false }: { kind: 'rw' | 'ro' | 'down' | 'st'; children: string; small?: boolean }) => {
  const bg = kind === 'rw' ? '#c9ffe6' : kind === 'ro' ? yellowSoft : kind === 'down' ? redSoft : amberSoft;
  const fg = kind === 'rw' ? deep : kind === 'ro' ? '#7a4f00' : kind === 'down' ? red : amber;
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: mono,
        fontSize: small ? 21 : 26,
        fontWeight: 700,
        padding: small ? '2px 12px' : '6px 18px',
        borderRadius: 999,
        background: bg,
        color: fg,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  );
};

const Card = ({ title, body, sub }: { title: string; body: string; sub?: string }) => (
  <div style={{ border: `2px solid ${border}`, borderRadius: 'var(--osd-radius)', background: '#fff', padding: '28px 36px' }}>
    <div style={{ fontFamily: mono, fontSize: 24, fontWeight: 700, color: deep, letterSpacing: '0.12em', textTransform: 'uppercase' }}>{title}</div>
    <div style={{ fontSize: 34, fontWeight: 600, marginTop: 14, lineHeight: 1.35 }}>{body}</div>
    {sub ? <div style={{ fontSize: 26, color: muted, marginTop: 10, lineHeight: 1.4 }}>{sub}</div> : null}
  </div>
);

const Stat = ({ value, label, sub }: { value: string; label: string; sub: string }) => (
  <div style={{ border: `2px solid ${border}`, borderRadius: 'var(--osd-radius)', background: '#fff', padding: '40px 44px' }}>
    <div style={{ fontFamily: mono, fontSize: 24, color: muted, letterSpacing: '0.12em', textTransform: 'uppercase' }}>{label}</div>
    <div style={{ fontSize: 96, fontWeight: 800, lineHeight: 1.05, color: 'var(--osd-accent)', marginTop: 8 }}>{value}</div>
    <div style={{ fontSize: 26, color: muted, marginTop: 8, lineHeight: 1.4 }}>{sub}</div>
  </div>
);

const Row = ({ name, mysql, jdbc, flight, overall, pad = '14px 18px' }: { name: string; mysql: string; jdbc: string; flight: string; overall: ReactNode; pad?: string }) => (
  <tr>
    <td style={{ padding: pad, borderBottom: `1px solid ${border}`, fontWeight: 600 }}>{name}</td>
    <td style={{ padding: pad, borderBottom: `1px solid ${border}`, fontFamily: mono, whiteSpace: 'nowrap' }}>{mysql}</td>
    <td style={{ padding: pad, borderBottom: `1px solid ${border}`, fontFamily: mono, whiteSpace: 'nowrap' }}>{jdbc}</td>
    <td style={{ padding: pad, borderBottom: `1px solid ${border}`, fontFamily: mono, whiteSpace: 'nowrap' }}>{flight}</td>
    <td style={{ padding: pad, borderBottom: `1px solid ${border}` }}>{overall}</td>
  </tr>
);

type Cell = { zh: string; rng: string; kind: 'rw' | 'ro' | 'down' | 'st' };
type DataRow = { id: string; name: string; mysql: Cell; jdbc: Cell; flight: Cell; overall: { zh: string; kind: 'rw' | 'ro' | 'down' | 'st' } };
const cellText = (c: Cell) => (c.rng === '—' ? c.zh : `${c.zh} ${c.rng}`);
const DataRows = ({ rows, pad, small = false }: { rows: DataRow[]; pad?: string; small?: boolean }) => (
  <>
    {rows.map((r) => (
      <Row key={r.id} pad={pad} name={r.name} mysql={cellText(r.mysql)} jdbc={cellText(r.jdbc)} flight={cellText(r.flight)} overall={<Level kind={r.overall.kind} small={small}>{r.overall.zh}</Level>} />
    ))}
  </>
);
const S = data.stats;

const Th = ({ children }: { children: string }) => (
  <th style={{ textAlign: 'left', padding: '12px 18px', background: surface, fontFamily: mono, fontSize: 22, letterSpacing: '0.1em', color: muted, textTransform: 'uppercase', fontWeight: 700 }}>
    {children}
  </th>
);

const Code = ({ children }: { children: string }) => (
  <pre
    style={{
      margin: 0,
      background: '#0f1a14',
      color: '#e6f4ee',
      borderRadius: 'var(--osd-radius)',
      padding: '32px 40px',
      fontFamily: mono,
      fontSize: 27,
      lineHeight: 1.55,
      whiteSpace: 'pre',
    }}
  >
    {children}
  </pre>
);

// ─────────────────────────────────────────────────────────────── pages

const Cover: Page = () => (
  <div style={{ ...fill, background: 'linear-gradient(180deg, #faf6ee 0%, #fffcf5 100%)', padding: '0 160px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <Eyebrow>Apache Doris 4.1.1 · GCP asia-east1 · 3 zones · 16 faults × 3 passes</Eyebrow>
    <h1 style={{ fontFamily: 'var(--osd-font-display)', fontSize: 'var(--osd-size-hero)', fontWeight: 800, lineHeight: 1.0, letterSpacing: '-0.035em', textTransform: 'uppercase', margin: '40px 0 0', maxWidth: 1500 }}>
      FE 掛了、BE 掛了、整台 VM 掛了，
      <br />
      <span style={{ color: 'var(--osd-accent)', background: `linear-gradient(transparent 62%, ${yellow} 62%)` }}>client 還能寫嗎？</span>
    </h1>
    <p style={{ fontSize: 40, color: muted, marginTop: 48, maxWidth: 1400, lineHeight: 1.5 }}>
      三種連線方式的 client（測試程式）每秒讀寫，16 種故障各做 3 輪，量 client 斷多久、還能不能寫、資料有沒有錯。
    </p>
    <Footer />
  </div>
);

const Architecture: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px', display: 'grid', gridTemplateColumns: '760px 1fr', gap: 64, alignItems: 'start' }}>
    <div>
      <Eyebrow>01 · Architecture</Eyebrow>
      <Heading>一個叢集，兩層各自 HA</Heading>
      <ul style={{ fontSize: 34, lineHeight: 1.5, marginTop: 36, paddingLeft: 40, color: 'var(--osd-text)' }}>
        <li style={{ marginBottom: 14 }}>3 台 VM（zone a/b/c），每台 1 個 FE + 1 個 BE</li>
        <li style={{ marginBottom: 14 }}>3 個 FE 都是 FOLLOWER（有投票權），以 <b>quorum</b> 選 1 個 master</li>
        <li style={{ marginBottom: 14 }}>3 個 BE 一個資料池，每份資料 <b>3 個 replica</b>，寫入要 2/3</li>
        <li style={{ marginBottom: 14 }}>client 帶三台 FE 主機清單，不經 LB</li>
        <li>FE + BE 同機只是 POC 省錢</li>
      </ul>
    </div>
    <img src={archNormal} alt="正常狀態架構" style={{ width: '100%', borderRadius: 'var(--osd-radius)', border: `2px solid ${border}`, background: '#fff', marginTop: 24 }} />
    <Footer />
  </div>
);

const Clients: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>02 · Clients</Eyebrow>
    <Heading>三個 client、同一套循環</Heading>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 32, marginTop: 48 }}>
      <Card title="mysql" body="Python + pymysql，FE :9030" sub="自己依主機清單 failover" />
      <Card title="jdbc" body="Java + Connector/J 多主機 URL" sub="driver 內建 failover" />
      <Card title="arrow-flight" body="Python + ADBC Flight SQL，FE :8070" sub="4.1.1 只支援查詢 → SELECT-only" />
    </div>
    <div style={{ marginTop: 56, fontFamily: mono, fontSize: 30, fontWeight: 700, color: deep, textAlign: 'center' }}>
      INSERT(ver=1) → UPSERT(ver=2) → SELECT 驗 ver=2 → DELETE → SELECT 驗不存在
    </div>
    <p style={{ fontSize: 30, color: muted, marginTop: 28, textAlign: 'center', lineHeight: 1.5 }}>
      每秒一步、每輪換一把 key、UNIQUE KEY 表；寫入失敗後另開連線做讀取檢查，才分得出「只讀」和「不可用」。
    </p>
    <Footer />
  </div>
);

const Design: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 72 }}>
    <div>
      <Eyebrow>03 · Design</Eyebrow>
      <Heading>故障矩陣</Heading>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 30, marginTop: 36, background: '#fff', border: `2px solid ${border}`, borderRadius: 16 }}>
        <tbody>
          <tr><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}`, fontFamily: mono, color: deep, fontWeight: 700, whiteSpace: 'nowrap' }}>對象</td><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}` }}>FE 程序 / BE 程序 / 整台 VM</td></tr>
          <tr><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}`, fontFamily: mono, color: deep, fontWeight: 700, whiteSpace: 'nowrap' }}>方式</td><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}` }}>crash（kill -9，自動重啟）/ dead（stop，不重啟）/ hang（kill -STOP 凍結）/ VM stop</td></tr>
          <tr><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}`, fontFamily: mono, color: deep, fontWeight: 700, whiteSpace: 'nowrap' }}>位置</td><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}` }}>master 所在 / follower 所在</td></tr>
          <tr><td style={{ padding: '16px 20px', fontFamily: mono, color: deep, fontWeight: 700, whiteSpace: 'nowrap' }}>雙重</td><td style={{ padding: '16px 20px' }}>VM 停 + FE dead · VM 停 + BE dead · 兩台 VM · 交錯</td></tr>
        </tbody>
      </table>
    </div>
    <div style={{ paddingTop: 140 }}>
      <div style={{ fontSize: 30, color: muted, marginBottom: 20 }}>結果等級（3 輪最差）</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20, fontSize: 32 }}>
        <div><Level kind="rw">讀寫正常</Level>　中斷後全部恢復</div>
        <div><Level kind="ro">只讀</Level>　寫入持續失敗、SELECT 正常</div>
        <div><Level kind="down">不可用</Level>　查詢也失敗</div>
        <div><Level kind="st">卡住</Level>　沒報錯也沒回應</div>
      </div>
      <p style={{ fontSize: 28, color: muted, marginTop: 36, lineHeight: 1.5 }}>
        中斷秒數 = 失敗時間 + 無回應時間（間隔 &gt; 5 秒）；等級看故障中最後 30 秒。設計用 OpenSpec 寫：每格一個 Scenario（WHEN / THEN 預期），實測數字另存 results/。
      </p>
    </div>
    <Footer />
  </div>
);

const Tooling: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px', display: 'grid', gridTemplateColumns: '780px 1fr', gap: 56, alignItems: 'start' }}>
    <div>
      <Eyebrow>04 · Tooling</Eyebrow>
      <Heading>資源、設定、動作</Heading>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 32 }}>
        <Card title="Terraform · infra/" body="GCP 上存在什麼" sub="4 台 VM、防火牆、API、vm_status 開關機、產生 Ansible inventory" />
        <Card title="Ansible · ansible/" body="機器裡長什麼樣" sub="JDK、Doris、conf、systemd、FE/BE 註冊、三個 probe" />
        <Card title="demo.sh" body="做一件事" sub="monitor / break / restore / measure；up、stop、start、down 薄包裝" />
      </div>
    </div>
    <img src={flow} alt="工具分工" style={{ width: '100%', borderRadius: 'var(--osd-radius)', border: `2px solid ${border}`, background: '#fff', marginTop: 200 }} />
    <Footer />
  </div>
);

const EnvState: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>05 · State machine</Eyebrow>
    <Heading>環境狀態機</Heading>
    <img src={envState} alt="環境狀態機" style={{ width: 1680, display: 'block', margin: '36px auto 0', borderRadius: 'var(--osd-radius)', border: `2px solid ${border}`, background: '#fff' }} />
    <p style={{ fontSize: 28, color: muted, marginTop: 24, textAlign: 'center' }}>
      break 可疊加、restore 依相反順序全部還原、crash 由 systemd 自動重啟；<span style={{ fontFamily: mono }}>demo.sh status</span> 隨時可看目前故障。
    </p>
    <Footer />
  </div>
);

const AvailState: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>06 · State machine</Eyebrow>
    <Heading>叢集可用性狀態機</Heading>
    <img src={availState} alt="叢集可用性狀態機" style={{ width: 1600, display: 'block', margin: '36px auto 0', borderRadius: 'var(--osd-radius)', border: `2px solid ${border}`, background: '#fff' }} />
    <p style={{ fontSize: 28, color: muted, marginTop: 24, textAlign: 'center' }}>
      FE ≥ 2 且 BE ≥ 2 才讀寫正常；BE = 1 只讀；FE = 1 不可用；master FE 被暫停但 TCP 還在 → 卡住。
    </p>
    <Footer />
  </div>
);

const Commands: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>07 · Commands</Eyebrow>
    <Heading>從零到一輪實驗</Heading>
    <div style={{ marginTop: 36 }}>
      <Code>{`./demo.sh up              # terraform apply → ansible → 灌 1 萬筆（約 10 分鐘）
./demo.sh monitor         # 終端 1：三個 client 即時捲動
./demo.sh break --target fe --mode hang --on master   # 終端 2：製造故障
./demo.sh restore         # 還原全部故障、等健康
./demo.sh measure         # 失敗時間、無回應時間、可用性等級

experiments/run_matrix.py --pass 1    # 開機 → 16 格 → 關機
experiments/finalize.sh               # 回填 spec → 產網站 → 部署
./demo.sh stop                        # 關機省錢；down = terraform destroy`}</Code>
    </div>
    <p style={{ fontSize: 28, color: muted, marginTop: 24 }}>任何指令加 <span style={{ fontFamily: mono }}>--dry-run</span> 只印出會執行的 gcloud / terraform / ansible 指令。</p>
    <Footer />
  </div>
);

const SingleResults: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>08 · Results</Eyebrow>
    <Heading>壞一個元件：{S.n_single_rw} / {S.n_single} 格讀寫正常</Heading>
    <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 22, marginTop: 16, background: '#fff', border: `2px solid ${border}` }}>
      <thead>
        <tr><Th>故障</Th><Th>mysql</Th><Th>jdbc</Th><Th>arrow-flight</Th><Th>結果</Th></tr>
      </thead>
      <tbody>
        <DataRows rows={data.single as DataRow[]} pad="5px 14px" small />
      </tbody>
    </table>
    <p style={{ fontSize: 22, color: muted, marginTop: 10 }}>秒數是 3 輪的中斷範圍（含 client 等 timeout）；正常的格子最慢 {S.ok_hi} 秒恢復，唯一例外是 master FE hang。</p>
    <Footer />
  </div>
);

const DoubleResults: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>09 · Results</Eyebrow>
    <Heading>同時壞兩個以上：由兩層各自的 quorum 決定</Heading>
    <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 28, marginTop: 32, background: '#fff', border: `2px solid ${border}` }}>
      <thead>
        <tr><Th>故障</Th><Th>mysql</Th><Th>jdbc</Th><Th>arrow-flight</Th><Th>結果</Th></tr>
      </thead>
      <tbody>
        <DataRows rows={data.double as DataRow[]} />
      </tbody>
    </table>
    <Steps>
      <div style={{ marginTop: 36, display: 'flex', flexDirection: 'column', gap: 16, fontSize: 32 }}>
        <Step><div>FE 剩 1/3 → <b>連查詢都失敗</b>：VM 停 + FE dead 3 輪 mysql / jdbc / arrow-flight 全部失敗</div></Step>
        <Step><div>BE 剩 1/3 → <b>能查、不能寫</b>：replica 湊不到 2/3，SELECT 由僅存的 replica 回</div></Step>
        <Step><div>兩層都 1/3 → <b>不可用</b>；交錯故障時僅存的 follower FE 還能回 mysql 的 SELECT，jdbc 不行，不能依賴</div></Step>
      </div>
    </Steps>
    <Footer />
  </div>
);

const Findings: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>10 · Findings</Eyebrow>
    <Heading>三個值得記住的發現</Heading>
    <Steps>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 28, marginTop: 32, fontSize: 28, lineHeight: 1.45 }}>
        <Step><div style={{ borderTop: `4px solid ${'var(--osd-accent)'}`, paddingTop: 16 }}><b>master FE hang：偵測慢又不穩定</b><br />{S.hang_txt}。FE 被凍結但 TCP port 還開著，其他 FE 一開始不覺得它掛了。</div></Step>
        <Step><div style={{ borderTop: `4px solid ${'var(--osd-accent)'}`, paddingTop: 16 }}><b>FE 剩 1/3 連查詢都不行</b><br />VM 停 + FE dead 3 輪全部失敗；交錯故障時僅存的 follower FE 還能回 mysql 的 SELECT，jdbc 不行。</div></Step>
        <Step><div style={{ borderTop: `4px solid ${'var(--osd-accent)'}`, paddingTop: 16 }}><b>client 先連 master 或 follower 差不多</b><br />mysql 先連 master {S.direct_mysql}、先連 follower {S.follower_mysql}；差別只在有沒有碰到 VM 關機期間等 timeout。</div></Step>
      </div>
    </Steps>
    <img src={timeline} alt="一次故障的時間軸" style={{ width: '100%', marginTop: 36, borderRadius: 'var(--osd-radius)', border: `2px solid ${border}`, background: '#fff' }} />
    <div style={{ fontSize: 24, color: soft, marginTop: 12, fontFamily: mono }}>
      停 master VM · 第 1 輪 · mysql client：break 後 {S.timeline.first_fail} 秒開始零星失敗（{S.timeline.n_windows} 次，最長 {S.timeline.max_secs} 秒，中斷共 {S.timeline.impact} 秒），restore 後 {S.timeline.restore_secs} 秒叢集回到健康
    </div>
    <Footer />
  </div>
);

const Consistency: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>11 · Consistency & recovery</Eyebrow>
    <Heading>資料正確性與恢復</Heading>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 32, marginTop: 48 }}>
      <Stat value={String(S.verify_fail)} label="資料錯誤" sub={`${S.n_runs} 次執行 · ${S.total_ops.toLocaleString()} 次操作，每次 SELECT 驗證`} />
      <Stat value="12 / 12" label="replica 正常" sub={`每次 restore 後 ${S.restore_min}～${S.restore_max} 秒回到 3 FE / 3 BE`} />
      <Stat value="0" label="人工介入" sub="VM 開回來 systemd 自動起 FE/BE、自動回到叢集" />
    </div>
    <p style={{ fontSize: 32, color: muted, marginTop: 56, lineHeight: 1.5, maxWidth: 1500 }}>
      寫入失敗就換一把新 key 重新開始，不會留下寫一半的資料；雙重故障恢復時，第二個元件回來的那一刻就恢復可寫。
    </p>
    <Footer />
  </div>
);

const Advice: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>12 · Recommendations</Eyebrow>
    <Heading>建議</Heading>
    <ul style={{ fontSize: 34, lineHeight: 1.5, marginTop: 40, paddingLeft: 44 }}>
      <li style={{ marginBottom: 20 }}><b>client</b>：JDBC 多主機連線字串最省事；自行實作時 timeout 2～3 秒、失敗重連時換下一台 FE；hang 時連線不會 reset，timeout 別設太長</li>
      <li style={{ marginBottom: 20 }}><b>架構</b>：正式環境 FE / BE 分機；FE 3 台是最低要求，掛 1 台就沒有備援</li>
      <li style={{ marginBottom: 20 }}><b>監控</b>：master 存在與 9030 timeout 要進告警，master hang 是唯一「沒報錯但不能用」的情境</li>
      <li style={{ marginBottom: 20 }}><b>寫入通道</b>：Arrow Flight SQL 只走查詢；寫入用 MySQL 協定或 Stream Load</li>
      <li><b>下一步</b>：網路分割、zone 故障、調 bdbje_heartbeat_timeout_second 縮短 hang 偵測</li>
    </ul>
    <Footer />
  </div>
);

const Closing: Page = () => (
  <div style={{ ...fill, background: '#0f1a14', color: '#f4fbf8', padding: '0 160px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
    <div style={{ fontFamily: mono, fontSize: 24, fontWeight: 700, letterSpacing: '0.18em', color: '#2ddfa8', textTransform: 'uppercase' }}>線上版 · 三頁 + 互動圖</div>
    <div style={{ fontFamily: 'var(--osd-font-display)', fontSize: 84, fontWeight: 800, lineHeight: 1.1, letterSpacing: '-0.03em', textTransform: 'uppercase', marginTop: 32, maxWidth: 1600 }}>
      精簡報告 → 實驗設計
      <br />→ 過程與結果
    </div>
    <div style={{ fontFamily: mono, fontSize: 40, color: '#ffd23f', marginTop: 48 }}>doris-ha-demo-195642473078.asia-east1.run.app</div>
    <p style={{ fontSize: 30, color: '#cfe3da', marginTop: 40, maxWidth: 1400, lineHeight: 1.5 }}>
      結果、log、spec、Terraform / Ansible、probe（測試程式）都在同一個 repo；experiments/finalize.sh 一鍵重產這些頁面。
    </p>
  </div>
);

export const meta: SlideMeta = {
  title: 'Doris 三節點 HA 故障矩陣實驗',
  createdAt: '2026-09-16T00:00:00.000Z',
};

export const notes: (string | undefined)[] = [
  '開場一句話：這個實驗回答的問題是「壞掉一個元件，client 還能不能寫」。網站三頁的順序是精簡報告、實驗設計、過程與結果，投影片照同樣順序。',
  '兩個數字決定後面所有結果：FE 要 3 台活 2 台（quorum）才能選 master、改 metadata；BE 寫入要 2/3 的 replica 成功。FE 與 BE 同機只是省錢。',
  'UNIQUE KEY 表讓同 key 的 INSERT 就是 UPSERT。寫入失敗後另開連線做讀取檢查，才分得出「只讀」和「不可用」。',
  '先講設計再講結果。四個等級要講清楚，尤其「卡住」是為 master hang 才加的：沒報錯，但等到 timeout 也沒回應。',
  '狀態交給宣告式工具，動作留在 shell。Terraform 只管 GCP 上存在什麼，Ansible 管機器裡長什麼樣，兩者都可重跑。',
  '環境狀態機：up 到健康、monitor、break 疊加、restore 依相反順序還原；stop/start 在健康與關機之間；down 回到未建立。',
  '叢集可用性：這張圖就是後面雙重故障結果的預測，實驗全部驗證了它。',
  '手動 demo 用 monitor + break + restore + measure 四個指令；整個矩陣交給執行器，一輪約 70 分鐘。',
  `壞一個元件 ${S.n_single_rw} / ${S.n_single} 格讀寫正常，最慢 ${S.ok_hi} 秒恢復。唯一例外是 master FE hang：${S.hang_txt}。`,
  '雙重故障：FE 剩 1/3 連查詢都不行，BE 剩 1/3 只讀，兩層都 1/3 不可用。交錯那格 mysql 還能讀是觀察到的例外，不能當保證。按 → 逐條講。',
  '三個發現按 → 逐條講：hang 偵測慢又不穩定、FE 1/3 連查詢都不行、先連 master 或 follower 差不多。下面是一次故障的時間軸。',
  `${S.n_runs} 次執行 0 筆資料錯誤，每次 restore 後 ${S.restore_min}～${S.restore_max} 秒自動回到 12 個 replica 正常，沒有人工介入。`,
  '建議：client 端換下一台 FE 與短 timeout；架構上 FE/BE 分機；監控要抓 master hang；寫入不要走 Flight SQL。',
  '結尾給連結，網站可以直接操作互動架構圖與每一格的 log。',
];

export default [Cover, Architecture, Clients, Design, Tooling, EnvState, AvailState, Commands, SingleResults, DoubleResults, Findings, Consistency, Advice, Closing] satisfies Page[];
