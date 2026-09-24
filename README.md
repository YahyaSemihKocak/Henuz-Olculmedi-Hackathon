# TEKNOFEST Kuantum Yazılım Yarışması — Su Dağıtım Ağları Optimizasyonu

**Takım Adı:** Henüz Ölçülmedi  
**Derece:** Türkiye 3.'lüğü  
**Konu:** Hibrit Kuantum-Klasik Algoritmalar ile Çok Dönemli Su Dağıtım Ağı ve Pompa Optimizasyonu  

---

## 📌 Proje Hakkında

Bu proje, şehir içi **Su Dağıtım Ağlarında (WDN - Water Distribution Networks)** enerji maliyetlerini minimize etmek, depo su seviyelerini optimize etmek ve pompa anahtarlama (açma-kapama) yıpranmalarını en aza indirmek amacıyla geliştirilmiş bir **Kuantum-Klasik Hibrit Optimizasyon** çözümüdür.

Problem, dinamik elektrik tarifeleri, kütle korunumu kısıtları ve fiziksel donanım limitleri altında **Kısıtlı Kuadratik Model (Constrained Quadratic Model - CQM)** olarak formüle edilmiş ve **D-Wave LeapHybridCQMSampler** ile çözülmüştür.

---

## 📐 Matematiksel Model Formülasyonu

Problem, $T$ zaman dilimi ($t \in \{1, \dots, T\}$), $P$ pompalar kümesi ($p \in \mathcal{P}$), $D$ depolar kümesi ($d \in \mathcal{D}$) ve $B$ boru hatları kümesi ($b \in \mathcal{B}$) üzerinde tanımlanmıştır.

### 1. Karar Değişkenleri (Decision Variables)

- $x_{p,t} \in \{0, 1\}$: $p$ pompasının $t$ zaman dilimindeki çalışma durumu ($1$: Açık, $0$: Kapalı).
- $V_{d,t} \in \mathbb{R}^+$: $d$ deposundaki su hacmi ($m^3$).
- $Q_{b,t} \in \mathbb{R}^+$: $b$ boru hattındaki akış debisi ($m^3/h$).

---

### 2. Amaç Fonksiyonu (Objective Function)

Amaç fonksiyonu, **toplam enerji maliyetini** ve **pompa yıpranma (anahtarlama) cezalarını** minimize etmeyi hedefler:

$$\min Z = \sum_{t=1}^{T} \sum_{p \in \mathcal{P}} \left( C_t \cdot E_p \cdot x_{p,t} \right) + \sum_{t=1}^{T} \sum_{p \in \mathcal{P}} S_p \cdot \vert{}x_{p,t} - x_{p,t-1}\vert{}$$

Burada:
- $C_t$: $t$ zaman dilimindeki birim elektrik tarifesi ($TL/kWh$).
- $E_p$: $p$ pompasının birim zamandaki enerji tüketimi ($kWh$).
- $S_p$: $p$ pompası için anahtarlama (açma-kapama) ceza katsayısı (Switching Penalty).

---

### 3. Fiziksel ve Operasyonel Kısıtlar (Constraints)

#### A. Kütle Korunumu ve Depo Denge Denklemi
Her $d$ deposu için $t$ anındaki su seviyesi, bir önceki dönemdeki seviye, giren akışlar, çıkan akışlar ve tüketim talebine ($D_{d,t}$) bağlıdır:

$$V_{d,t} = V_{d,t-1} + \Delta t \left( \sum_{p \in \text{In}(d)} Q_{p,t} + \sum_{b \in \text{In}(d)} Q_{b,t} - \sum_{b \in \text{Out}(d)} Q_{b,t} - D_{d,t} \right), \quad \forall d \in \mathcal{D}, \, \forall t \in \{1, \dots, T\}$$

#### B. Depo Kapasite Sınırları
Depoların taşmasını ve kurumasını önlemek için min/max hacim sınırları:

$$V_{d,\min} \le V_{d,t} \le V_{d,\max}, \quad \forall d \in \mathcal{D}, \, \forall t \in \{1, \dots, T\}$$

#### C. Pompa Akış ve Kapasite Kısıtları
Bir pompadan geçen akış, pompanın açık/kapalı durumuna göre belirlenir:

$$Q_{p,t} = Q_{p,\max} \cdot x_{p,t}, \quad \forall p \in \mathcal{P}, \, \forall t \in \{1, \dots, T\}$$

#### D. Periyodik Sınır Koşulu (Periodic Boundary Condition)
Planlama dönemi sonunda depoların tükenmemesini sağlamak amacıyla:

$$V_{d,T} \ge V_{d,0}, \quad \forall d \in \mathcal{D}$$

---
