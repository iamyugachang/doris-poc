import type { ReactNode } from 'react';
import type { DesignSystem, Page, SlideMeta } from '@open-slide/core';
import { Step, Steps, useSlidePageNumber } from '@open-slide/core';

import archNormal from './assets/arch-normal.svg';
import archDown from './assets/arch-down.svg';
import flow from './assets/flow.svg';
import envState from './assets/env-state.svg';
import availState from './assets/avail-state.svg';
import timeline from './assets/timeline.svg';

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

const Level = ({ kind, children }: { kind: 'rw' | 'ro' | 'down' | 'st'; children: string }) => {
  const bg = kind === 'rw' ? '#c9ffe6' : kind === 'ro' ? yellowSoft : kind === 'down' ? redSoft : amberSoft;
  const fg = kind === 'rw' ? deep : kind === 'ro' ? '#7a4f00' : kind === 'down' ? red : amber;
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: mono,
        fontSize: 26,
        fontWeight: 700,
        padding: '6px 18px',
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

const Row = ({ name, mysql, jdbc, flight, overall }: { name: string; mysql: string; jdbc: string; flight: string; overall: ReactNode }) => (
  <tr>
    <td style={{ padding: '14px 18px', borderBottom: `1px solid ${border}`, fontWeight: 600 }}>{name}</td>
    <td style={{ padding: '14px 18px', borderBottom: `1px solid ${border}`, fontFamily: mono }}>{mysql}</td>
    <td style={{ padding: '14px 18px', borderBottom: `1px solid ${border}`, fontFamily: mono }}>{jdbc}</td>
    <td style={{ padding: '14px 18px', borderBottom: `1px solid ${border}`, fontFamily: mono }}>{flight}</td>
    <td style={{ padding: '14px 18px', borderBottom: `1px solid ${border}` }}>{overall}</td>
  </tr>
);

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
      三種協定的 client 每秒讀寫，我們把 16 種故障各注入三輪，量中斷幾秒、還能不能寫、資料有沒有不一致。
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
        <li style={{ marginBottom: 14 }}>FE 三個 FOLLOWER，<b>多數決</b>選 1 個 master</li>
        <li style={{ marginBottom: 14 }}>BE 一個資料池，每個 tablet <b>三副本</b>，寫入要 2/3</li>
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
          <tr><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}`, fontFamily: mono, color: deep, fontWeight: 700, whiteSpace: 'nowrap' }}>方式</td><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}` }}>crash（kill -9）/ dead（stop）/ hang（SIGSTOP）/ VM stop</td></tr>
          <tr><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}`, fontFamily: mono, color: deep, fontWeight: 700, whiteSpace: 'nowrap' }}>位置</td><td style={{ padding: '16px 20px', borderBottom: `1px solid ${border}` }}>master 所在 / follower 所在</td></tr>
          <tr><td style={{ padding: '16px 20px', fontFamily: mono, color: deep, fontWeight: 700, whiteSpace: 'nowrap' }}>雙重</td><td style={{ padding: '16px 20px' }}>VM 停 + FE dead · VM 停 + BE dead · 兩台 VM · 交錯</td></tr>
        </tbody>
      </table>
    </div>
    <div style={{ paddingTop: 140 }}>
      <div style={{ fontSize: 30, color: muted, marginBottom: 20 }}>可用性等級（三輪最差）</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20, fontSize: 32 }}>
        <div><Level kind="rw">讀寫正常</Level>　中斷後全部恢復</div>
        <div><Level kind="ro">只讀</Level>　寫入持續失敗、SELECT 正常</div>
        <div><Level kind="down">不可用</Level>　查詢也失敗</div>
        <div><Level kind="st">卡住</Level>　沒報錯也沒回應</div>
      </div>
      <p style={{ fontSize: 28, color: muted, marginTop: 36, lineHeight: 1.5 }}>
        受影響秒數 = 失敗視窗 ∪ 卡頓（間隔 &gt; 5s）；等級看故障中最後 30 秒。規格用 OpenSpec：每格一個 Scenario，跑完由工具回填三輪實測。
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
        <Card title="Ansible · ansible/" body="機器裡長什麼樣" sub="JDK、Doris、conf、systemd、FE/BE 註冊、三個探測" />
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
      break 可疊加、restore 逆序全部逆轉、crash 由 systemd 自動拉起；<span style={{ fontFamily: mono }}>demo.sh status</span> 隨時可看目前故障。
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
./demo.sh break --target fe --mode hang --on master   # 終端 2：注入故障
./demo.sh restore         # 逆轉全部故障、等健康
./demo.sh measure         # 失敗視窗、卡頓、可用性等級

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
    <Heading>單一故障：12 格全部讀寫正常</Heading>
    <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 28, marginTop: 32, background: '#fff', border: `2px solid ${border}` }}>
      <thead>
        <tr><Th>故障</Th><Th>mysql</Th><Th>jdbc</Th><Th>arrow-flight</Th><Th>結論</Th></tr>
      </thead>
      <tbody>
        <Row name="停 master VM（三種 client 順序）" mysql="0～37s" jdbc="1～39s" flight="0～30s" overall={<Level kind="rw">讀寫正常</Level>} />
        <Row name="停 follower VM" mysql="0～25s" jdbc="2～19s" flight="2～20s" overall={<Level kind="rw">讀寫正常</Level>} />
        <Row name="master FE crash / dead" mysql="0～28s" jdbc="1～29s" flight="6～9s" overall={<Level kind="rw">讀寫正常</Level>} />
        <Row name="follower FE crash / hang" mysql="1～28s" jdbc="1～48s" flight="2～39s" overall={<Level kind="rw">讀寫正常</Level>} />
        <Row name="BE crash / dead / hang" mysql="6～37s" jdbc="6～36s" flight="1～31s" overall={<Level kind="rw">讀寫正常</Level>} />
        <Row name="master FE hang（SIGSTOP）" mysql="63～136s" jdbc="69～136s 卡住" flight="每筆 9s" overall={<Level kind="st">卡住</Level>} />
      </tbody>
    </table>
    <p style={{ fontSize: 26, color: muted, marginTop: 20 }}>秒數是三輪的受影響範圍；差異來自 client 是否卡在「VM 關機那 25 秒」裡轉發給快消失的 master。</p>
    <Footer />
  </div>
);

const DoubleResults: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>09 · Results</Eyebrow>
    <Heading>雙重故障：由兩層的多數決決定</Heading>
    <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 28, marginTop: 32, background: '#fff', border: `2px solid ${border}` }}>
      <thead>
        <tr><Th>故障</Th><Th>mysql</Th><Th>jdbc</Th><Th>arrow-flight</Th><Th>結論</Th></tr>
      </thead>
      <tbody>
        <Row name="VM 停 + 另一台 FE dead（FE 1/3）" mysql="不可用" jdbc="不可用" flight="讀取失敗" overall={<Level kind="down">不可用</Level>} />
        <Row name="VM 停 + 另一台 BE dead（BE 1/3）" mysql="只讀" jdbc="只讀" flight="讀取正常" overall={<Level kind="ro">只讀</Level>} />
        <Row name="兩台 VM 停" mysql="不可用" jdbc="卡住" flight="讀取失敗" overall={<Level kind="down">不可用</Level>} />
        <Row name="交錯：VM 停 + BE dead + FE dead" mysql="不可用 / 只讀" jdbc="不可用 / 只讀" flight="失敗 / 正常" overall={<Level kind="down">不可用</Level>} />
      </tbody>
    </table>
    <Steps>
      <div style={{ marginTop: 36, display: 'flex', flexDirection: 'column', gap: 16, fontSize: 32 }}>
        <Step><div>FE 剩 1/3 → <b>連查詢都拿不到 metadata</b>：僅存 follower 拒絕連線，僅存 master 全部逾時</div></Step>
        <Step><div>BE 剩 1/3 → <b>寫入失敗、讀取正常</b>：第 2、3 輪由讀取檢查直接證實</div></Step>
        <Step><div>兩層都 1/3 → 看僅存那個 FE 是否 master，三輪出現「不可用」與「只讀」兩種</div></Step>
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
        <Step><div style={{ borderTop: `4px solid ${'var(--osd-accent)'}`, paddingTop: 16 }}><b>master FE hang 偵測不穩定</b><br />第 1 輪 2 分鐘沒選主、第 2/3 輪 63 秒才選主。BDB JE 心跳只看 TCP 是否存活。</div></Step>
        <Step><div style={{ borderTop: `4px solid ${'var(--osd-accent)'}`, paddingTop: 16 }}><b>FE 剩 1/3 連讀都不行</b><br />僅存 follower 拒絕連線，僅存 master 全部逾時。</div></Step>
        <Step><div style={{ borderTop: `4px solid ${'var(--osd-accent)'}`, paddingTop: 16 }}><b>中斷長短不看連 master 或 follower</b><br />看有沒有卡在關機那 25 秒的轉發逾時：碰到 20～40 秒，沒碰到 0～2 秒。</div></Step>
      </div>
    </Steps>
    <img src={timeline} alt="一次故障的時間軸" style={{ width: '100%', marginTop: 36, borderRadius: 'var(--osd-radius)', border: `2px solid ${border}`, background: '#fff' }} />
    <div style={{ fontSize: 24, color: soft, marginTop: 12, fontFamily: mono }}>停 master VM · 第 1 輪 · mysql client 視角：break 後 4 秒失敗、29 秒後恢復，restore 後 61 秒叢集回到健康</div>
    <Footer />
  </div>
);

const Consistency: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>11 · Consistency & recovery</Eyebrow>
    <Heading>資料一致性與恢復</Heading>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 32, marginTop: 48 }}>
      <Stat value="0" label="資料不一致" sub="48 次執行的 SELECT 驗證" />
      <Stat value="12 / 12" label="副本 OK" sub="每次 restore 後都回到 3 FE / 3 BE" />
      <Stat value="0" label="人工介入" sub="VM 開回來 systemd 自動起 FE/BE、自動歸隊" />
    </div>
    <p style={{ fontSize: 32, color: muted, marginTop: 56, lineHeight: 1.5, maxWidth: 1500 }}>
      寫入在中斷視窗內失敗會換新 key 重來，不留下半套資料；雙重故障恢復時，第二個元件回來的那一刻就恢復可寫。
    </p>
    <Footer />
  </div>
);

const Advice: Page = () => (
  <div style={{ ...fill, padding: '100px 120px 120px' }}>
    <Eyebrow>12 · Recommendations</Eyebrow>
    <Heading>建議</Heading>
    <ul style={{ fontSize: 34, lineHeight: 1.5, marginTop: 40, paddingLeft: 44 }}>
      <li style={{ marginBottom: 20 }}><b>client</b>：JDBC 多主機 URL 最省事；自行實作時逾時 2～3 秒、失敗重連時輪替主機</li>
      <li style={{ marginBottom: 20 }}><b>架構</b>：正式環境 FE / BE 分機；FE 3 台是最低要求，掛 1 台就沒有冗餘</li>
      <li style={{ marginBottom: 20 }}><b>監控</b>：master 存在與 9030 逾時要進告警，master hang 是唯一「沒報錯但不能用」的情境</li>
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
      結果、log、spec、Terraform / Ansible、探測程式都在同一個 repo；experiments/finalize.sh 一鍵重產這些頁面。
    </p>
  </div>
);

export const meta: SlideMeta = {
  title: 'Doris 三節點 HA 故障矩陣實驗',
  createdAt: '2026-09-11T00:38:18.251Z',
};

export const notes: (string | undefined)[] = [
  '開場一句話：這個實驗回答的問題是「掛掉一個元件，client 還能不能寫」。網站三頁的順序是精簡報告、實驗設計、過程與結果，投影片照同樣順序。',
  '兩個數字決定後面所有結果：FE 需要 2/3 才能選 master 與改 metadata；BE 寫入需要 2/3 副本成功。FE 與 BE 同機只是省錢。',
  'UNIQUE KEY 表讓同 key 的 INSERT 就是 UPSERT。讀取檢查是第 2 輪起加的，第 1 輪靠 flight 的讀取結果推斷只讀。',
  '先講設計再講結果。四個等級要講清楚，尤其「卡住」是為 master hang 才加的：沒報錯，但等到逾時也沒回應。',
  '狀態交給宣告式工具，動作留在 shell。Terraform 只管 GCP 上存在什麼，Ansible 管機器裡長什麼樣，兩者都可重跑。',
  '環境狀態機：up 到健康、monitor、break 疊加、restore 逆序逆轉；stop/start 在健康與關機之間；down 回到未建立。',
  '叢集可用性：這張圖就是後面雙重故障結果的預測，實驗全部驗證了它。',
  '手動 demo 用 monitor + break + restore + measure 四個指令；整個矩陣交給執行器，一輪約 70 分鐘。',
  '單一故障全部讀寫正常。秒數是三輪範圍，差異來自 client 是否卡在轉發給快消失的 master。唯一例外是 master hang。',
  '雙重故障：FE 剩 1/3 連讀都不行，BE 剩 1/3 只讀，兩層都 1/3 看僅存 FE 是否 master。按 → 逐條講。',
  '三個發現按 → 逐條講：hang 偵測不穩定、FE 1/3 連讀都不行、中斷長短看有沒有碰到關機期間的轉發逾時。右邊是一次故障的時間軸。',
  '48 次執行 0 不一致，每次都自動回到 12 副本 OK，沒有人工介入。',
  '建議：client 端輪替主機與短逾時；架構上 FE/BE 分機；監控要抓 master hang；寫入不要走 Flight SQL。',
  '結尾給連結，網站可以直接操作互動架構圖與每一格的 log。',
];

export default [Cover, Architecture, Clients, Design, Tooling, EnvState, AvailState, Commands, SingleResults, DoubleResults, Findings, Consistency, Advice, Closing] satisfies Page[];
