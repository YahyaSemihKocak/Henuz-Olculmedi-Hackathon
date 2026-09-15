# **Su Dağıtım Şebekesi Dinamik Kaynak Tahsisi** 

### **Problem Çözüm Raporu** 

**Takım Adı: HENÜZ ÖLÇÜLMEDİ** 

#### **Özet** 

Bu raporda, TEKNOFEST Su Dağıtım Şebekesi Dinamik Kaynak Tahsisi yarışması kapsamında Problem 1 için kullanılan QUBO matrisi çözümü ile Problem 2, 3 ve 4 için geliştirilen Kuantum Büyük Komşuluk Arama (Q-LNS) ve Hibrit CQM/LP yaklaşımı detaylandırılmaktadır. Geliştirilen yöntem; klasik Doğrusal Programlama (LP) gevşetmesi, D- Wave Kısıtlı Kuadratik Model (CQM) ile kuantum tavlama ve CBC çözücüsü ile dal-sınır (branch-and-bound) optimizasyonunu birleştiren izlenebilir, hibrit bir boru hattı (pipeline) sunmaktadır. 

## **1. Giriş ve Problem Tanımı** 

- **Problem 1:** On iki pompalı bir su dağıtım alt şebekesinde işletim maliyetini minimize ederken alt talep ve üst kapasite kısıtlarını sağlayan optimal pompa konfigürasyonunun belirlenmesi; sistemin QUBO formuna dönüştürülüp kuantum işlemci (QPU) üzerinde çözülmesini gerektiren bir kombinatoryal optimizasyon problemidir. 

- **Problem 2:** Tek dönemlik (24 saat) bir su dağıtım şebekesinde kaynak üretimi, pompa durumları, hat akışları, depo stok dengesi ve talep karşılama kararlarını eş zamanlı optimize ederek toplam işletme maliyetini ve ceza fonksiyonlarını en aza indiren Karma Tamsayılı Doğrusal Programlama (MILP) problemidir. 

- **Problem 3:** Problem 2’deki temel tahsis altyapısını genişleterek bölge taleplerini kritik ve normal olarak ayrıştıran; kaynak veya hat kısıtları altında kesintileri rastgele maliyet yerine tüketici önceliğine göre yöneten sistematik kısıntı planlaması (curtailment) modelidir. 

- **Problem 4:** Problem 2’deki şebekenin tam sağlamlık varsayımını kaldırarak arızalı hatların kapasitesini sıfırlayan; şebeke dayanıklılığını (resilience) analiz edip alternatif güzergâhlar, yedek kaynaklar ve depo tamponlaması üzerinden operasyonel akışı yeniden yapılandıran MILP modelidir. 

## **2. Problem 1: Pompa Kombinasyonu Seçimi ve QUBO Formülasyonu** 

On iki pompalık alt şebekede her pompa ya tam kapasitesiyle çalışır ya da hiç çalışmaz. Amaç, toplam debiyi talep ile üst kapasite sınırı arasında tutan ve toplam işletme maliyetini en aza indiren pompa kombinasyonunu bulmaktır. 

### **2.1 Klasik Model** 

Her pompanın durumu 𝑦𝑖 ∈0,1, 𝑖= 0, … ,11 ile ikili bir karar değişkeni olarak ifade edilir. Toplam talep D = 1025,2 m3/sa ve kapasite üst sınırı 𝑄𝑚𝑎𝑥 = 1148,2 m³/sa olarak verilmiştir. Problem, kısıtlı bir minimizasyon problemi olarak aşağıdaki gibi kurulur: 



Burada 𝐶𝑖 pompanın maliyetini 𝑄𝑖ise pompanın kapasitesini temsil eder. 

### **2.2 QUBO Dönüşümü** 

Kısıtlı problemi bir QUBO’ya taşımak için amaç ve kısıtlar ortak bir Hamiltoniyende birleştirilir. Eşitsizlik kısıtları, ikili tabanda kodlanan gevşeklik (slack) değişkenleri aracılığıyla kuadratik ceza terimlerine dönüştürülür: 



𝛼 𝑣𝑒 𝛽 ceza katsayıları, kısıtların sağlanmasını maliyet minimizasyonundan daha öncelikli kılacak şekilde 𝛼= 𝛽 = 100,0 seçilmiştir. Gevşeklik değişkenleri ikili seriler halinde modellendiğinden (𝑗= 0, . . . ,10, ℎ𝑒𝑟 𝑘𝚤𝑠𝚤𝑡 𝑖ç𝑖𝑛 11 𝑏𝑖𝑡),  toplam değişken sayısı 12 + 11 + 11 = 34’e ulaşmaktadır. Kareler açılarak kuadratik terimler elde edilir: 



<!-- Start of picture text -->
ll ll ll ll 10<br>H= >> Cy + a( au +> SS 20:Qiviyj + D? +30 4's,<br>i=0 i=0 i=0 j=i+1 i=0<br>10 10 ll ll 10 10<br>+2 2s1is5 — So 2DQw — YOY 202 visig + Yo 2D2s1s)<br>i=0 j=i+1 i=0 i=0 j=0 i=0<br>ll ll ll 10<br>+ (> Qui + 2 YS 2QiQj ij + Qrae + ¥24's2,<br>i=0 i=0 j=i+1 i=0<br>10 10 il ll 10 10<br>+ 5 YF 247 Ys25825 — D2 2Q maz Qigh + 2 > 20:2 i825 — J 2Q mas 282) (4)<br>i=0 j=i+1 i=0 i=0 j=0 i=0<br><!-- End of picture text -->

Sayısal katsayılar yerine konulduğunda, D-Wave kuantum tavlayıcısında doğrudan çözülebilecek **Q** matrisi elde edilir: 



Elde edilen **Q** matrisi D-Wave mimarisine gömülerek taban durum (ground state) analizi ile çözülmüş ve sonuç **qubo_matrix.json** dosyasına kaydedilmiştir. 

### **2.3 Problem 1 Sayısal Çözüm Özeti** 

Tablo 1: Problem 1 sayısal sonuçları. 

|**Metrik**|**Değer**|
|---|---|
|Amaç Fonksiyonu Değeri|4689.2 TL|
|Su Miktarı|1058 m³|
|Talep Karşılama|%100|
|Aktif Pompa|5 / 12|



• **0, 3, 4, 6 ve 10 numaralı borular problemin çözümünde kullanılmaktadır.** 

## **3. Problem 2: Temel Tahsis Modeli ve Çözüm Yöntemi** 

Klasik MILP modeli PuLP kütüphanesiyle kurulur (K1–K16 kısıtlarının tamamı eklenerek). İkili kaynak açılış (w) ve pompa çalışma (y) değişkenleri sürekli uzaya [0,1] çekilerek CBC çözücüsüyle hızlı bir alt sınır (lower bound ) ve kesirli bir çekirdek (fractional core) elde edilir. 

Benders decomposition ve Quantum LNS decomposition algoritmalarından ilham alan kendi yöntemimizi yaptık. 

### **Kesirli Çekirdek (Fractional Core)** 

Karmaşık tamsayılı programlama (MILP) modellerinde ikili (binary) karar değişkenleri **[0, 1]** sürekli uzayına çekilerek Doğrusal Programlama (LP) gevşetmesi çözüldüğünde, değişkenlerin bir kısmı doğrudan uç değerleri (0 veya 1) alırken bir kısmı kesirli değerler (0 < x < 1) alır. 

LP çözümü sonucunda tam 0 veya 1 değerine oturamayıp kesirli kalan bu ikili değişkenlerin oluşturduğu alt kümeye kesirli çekirdek (fractional core) denir. Matematiksel olarak şu şekilde tanımlanır: 



<!-- Start of picture text -->
C=f{ielle<aj<1-¢6<br><!-- End of picture text -->

### **Dal-Sınır ve Onarım Döngüleri** 

Kuantum adımından dönen örneklemler bir başlangıç çözümü (warm start) olarak PuLP modeline geri beslenir. Yalnızca hedeflenen serbest değişkenler ikili bırakılarak problem daraltılmış bir uzayda kesin olarak çözülür. Gevşeklik ihlali olması durumunda, serbest bırakılan değişken kümesi kademeli olarak genişletilerek onarım turları (repair rounds) uygulanır ve çözüm is_feasible rutini ile bağımsız olarak doğrulanır. 

### **Sıcak Başlangıç (Warm Start)** 

Karmaşık optimizasyon ve tamsayılı programlama (MILP) modellerinde çözücünün arama uzayını sıfırdan taraması yerine, önceden elde edilmiş kaliteli bir uygun (feasible) veya yaklaşık çözümün sisteme **başlangıç noktası** olarak verilmesi yöntemine **sıcak başlangıç (warm start)** denir. 

Matematiksel olarak, karar değişkenleri optimizasyon başlamadan önce öncül değerlerle ilklendirilir: 



<!-- Start of picture text -->
0), « .<br>v8 (Viel)<br><!-- End of picture text -->

## **4. Problem 3: Kritik Talep Önceliklendirme ve Kısıntı Modellemesi** 

Problem 2’nin “tüm talep eşittir” varsayımı kaldırılır: hastane, itfaiye, okul ve kritik altyapı gibi kesintiye tahammülü olmayan tüketiciler **kritik talep** , geri kalan konut/ticari tüketim ise normal talep olarak ayrıştırılır. Kaynak yetersizliği, hat tıkanıklığı veya depo boşalması durumunda modelin yapacağı tercih artık rastgele değil, tüketici önceliğine göre şekillenir: kritik bölgeye su ulaştırmak için daha pahalı bir güzergâh kullanmak ya da normal bölgelerde kesinti yapmak tercih edilebilir. Bu, sistematik bir kısıntı planlaması sağlar. 

### **4.1 Parametreler ve Karar Değişkenleri** 

- 𝑑𝑧𝑁, 𝑑𝑧𝐾: 𝑧 bölgesinin normal ve kritik talep debisi (m³ / sa) 

- 𝑑𝑧 = 𝑑𝑧𝑁 + 𝑑𝑧𝐾: 𝑧 bölgesinin toplam talebi (m³ /sa) 

- 𝑢𝑧𝑁, 𝑢𝑧𝐾 ≥0: 𝑧 bölgesinde karşılanamayan normal ve kritik talep debisi 

- Π𝑡𝑎𝑙= 25.000(𝑇𝐿/𝑚)<sup>3</sup> : normal talep kısıntı birim cezası 

- 10 ⋅Π𝑡𝑎𝑙= 250.000(𝑇𝐿/𝑚)<sup>3</sup> : kritik talep kısıntı birim cezası (10× öncelik) 

- 𝑇= 24,0(𝑠𝑎𝑎𝑡): planlama dönemi 

### **4.2 Güncellenen Amaç Fonksiyonu** 



𝑇Π<sup>𝑡𝑎𝑙</sup> ∑𝑢𝑧𝑁 terimi karşılanamayan normal talep için ödenen cezayı, 10𝑇Π𝑡𝑎𝑙 ∑𝑢𝑧𝐾 terimi ise karşılanamayan kritik talep için ödenen yüksek öncelikli cezayı ifade eder. 

### **4.3 Güncellenen Kısıtlar** 

**Düğüm Akış Dengesi (K6):** talep noktalarında fiilen teslim edilen debi (𝑑𝜁(𝑛) −𝑢𝜁(𝑛)<sup>𝑁</sup> − 𝑢𝜁(𝑛)<sup>𝐾</sup> ) olarak dengeye dahil edilir: 





**Kısıntı Üst Sınırları (K16):** kısıntı miktarı negatif olamaz ve mevcut talebi aşamaz: 0 ≤𝑢𝑧𝑁 ≤𝑑𝑧𝑁(𝑣𝑒)0 ≤𝑢𝑧𝐾 ≤𝑑𝑧𝐾, ∀𝑧∈𝑍   (8) 

### **4.4 Problem 3 Sayısal Çözüm Özeti** 

Sonuçlar **demand_service.csv** dosyasına [zone_id, unmet_normal_m3h, unmet_critical_m3h] formatında kaydedilmiştir. 

Tablo 2: Problem 3 sayısal sonuçları. 

|**Metrik**|**Değer / Açıklama**|
|---|---|
|Toplam Talep (24 sa)|1.746.963,36 m3 (1.644.212,88 Normal + 102.750,48 Kritik)|
|Kritik Talep Karşılama|%100,00 (0,00 m3 karşılanamayan)|
|Normal Talep Karşılama|%100,00 (0,00 m3 karşılanamayan)|
|Kısıntı Ceza Tutarı|0,00 TL|
|Amaç Fonksiyonu Değeri|20.302.930,22 TL|
|LP Alt Sınırı / Gap|14.306.185,25 TL (%41,92)|
|Aktif Pompa / Kaynak|152 / 82|
|Fizibilite|EVET (K1–K16 tam doğrulanmıştır)|



## **5. Problem 4: Şebeke Hasarı ve Arızalı Hat Yönetimi** 

Problem 2’nin “bütün hatlar sağlam ve çalışır durumdadır” varsayımı Problem 4 kapsamında kaldırılmıştır. Fiziksel boru patlakları ve arızalar sonucunda 45.702 yönlü arkın 5.981’i dönem boyunca tamamen kullanılamaz hale gelmiştir. Modelin amacı, hasarlı hatları baypas ederek, alternatif terfi güzergâhlarını ve ara depoları tampon olarak kullanmak suretiyle şebekede oluşabilecek kısıntıları en aza indirmektir. 

### **5.1 Parametreler ve Kümeler** 

- 𝐴𝑢𝑛𝑎𝑣 ⊂𝐴: kullanılamaz/arızalı arklar kümesi (|𝐴𝑢𝑛𝑎𝑣| = 5.981) 

- 𝛼𝑎 ∈{0,1}: 𝑎 arkının kullanılabilirlik durumu (𝑎∈𝐴𝑢𝑛𝑎𝑣 ⇒𝛼𝑎 = 0, aksi halde 𝛼𝑎 = 1) 

- 𝑥̅𝑎: 𝑎 arkının nominal iletim kapasitesi (𝑚<sup>3</sup> /𝑠𝑎) 

- 𝑑𝑧: 𝑧 bölgesinin toplam su talebi debisi (𝑚<sup>3</sup> /𝑠𝑎) 

- 𝑢𝑧 ∈[0, 𝑑𝑧]: 𝑧 bölgesinde karşılanamayan toplam talep debisi (𝑚<sup>3</sup> /𝑠𝑎) 

- Π<sup>𝑡𝑎𝑙</sup> = 25.000 TL/m<sup>3</sup> : karşılanamayan talep kısıntı birim cezası 

- Π<sup>𝑡𝑢𝑘</sup> = 25 TL/m<sup>3</sup> : depo güvenlik stoğu tüketimi fırsat maliyeti 

### **5.2 Güncellenen Ark Kapasite Kısıtı (K3)** 

Arızalı hatlardan su geçişine izin verilmez; ark debisi kullanılabilirlik katsayısıyla sıfırlanır: 



Yani arızalı boru hatlarının taşıma kapasitesi fiilen sıfıra çekilir. 

### **5.3 Amaç Fonksiyonu ve Depo Tamponlama Mekanizması** 

Talep kısıntısı, Problem 2’deki tekil uz değişkeni üzerinden modellenir: 



𝑇Π<sup>𝑡𝑎𝑙</sup> ∑𝑧∈𝑍 𝑢𝑧 terimi iletim hatlarının kopması sonucu oluşabilecek su kesintisi cezasını, Π<sup>𝑡𝑢𝑘</sup> ∑𝑟∈𝑅 𝜖𝑟𝑡𝑢𝑘 terimi ise boruları kesilen izole bölgeleri beslemek amacıyla depolardaki başlangıç güvenlik stoğunun (𝑉𝑟0) tüketilmesinin fırsat maliyetini ifade eder. Bu mekanizma, hasar altında depoların tampon görevi görmesini ve alternatif güzergâhların, yedek kaynakların devreye girmesini sağlar. 

### **5.4 Problem 4 Sayısal Çözüm Özeti** 

Tablo 3: Problem 4 sayısal sonuçları. 

|**Metrik**|**Değer / Açıklama**|
|---|---|
|Kullanılamayan / Arızalı Ark|5.981𝑎𝑑𝑒𝑡(𝑥𝑎= 0,00m<sup>3</sup>/sa doğrulanmıştır)|
|Toplam Talep (24 sa)|1.746.963,36 m³|
|Karşılanamayan Talep (u)|0,00 m³ (%100,00 karşılama)|
|Kısıntı Ceza Tutarı|0,00 TL|
|Depo Fırsat Maliyeti|12.962.083,20 TL (226 deponun suyu kullanılmıştır)|
|Amaç Fonksiyonu Değeri|27.268.729,54 TL|
|LP Alt Sınırı / Gap|21.035.192,53 TL (%29,63)|
|Aktif Pompa / Kaynak|141 / 76|
|Fizibilite|EVET (K1–K16, sıfır taban ihlaliyle sağlanmıştır)|



## **6. Bulgular ve Metrikler** 

Tablo 4, geliştirilen algoritmanın dört problem üzerindeki performansını özetlemektedir. Veriler solution_summary.json çıktılarından derlenmiştir. 

Tablo 4: Problem bazlı çözüm performans metrikleri. 

|**Metrik**|**Prob 1**|**Prob 2**|**Prob 3**|**Prob 4**|
|---|---|---|---|---|
|Amaç Değeri (TL)|4689.2|450.210,00|20.302.930,22|27.268.729,54|
|Talep Karşılama|%100|%100|%100|%100|
|LP Alt Sınır Farkı|—|%0,05|%41,92|%29,63|
|Çalışan Pompa|5 / 12|1.420|152 / 82|141 / 76|



## **7. Kaynakça ve Üçüncü Taraf Araç Bildirimi** 

[1] Takabayashi, Taisei, and Masayuki Ohzeki. "Hybrid algorithm of linear programming relaxation and quantum annealing." Journal of the Physical Society of Japan 93.3 (2024): 034001. 

[2] Boschetti, Marco A., et al. "Matheuristics: Optimization, simulation and control." International workshop on hybrid metaheuristics. Berlin, Heidelberg: Springer Berlin Heidelberg, 2009. 

[3] Pang, Yuchen, et al. "The potential of quantum annealing for rapid solution structure identification." Constraints 26.1 (2021): 1-25. 

[4] Podobrii, Mikhail, et al. "Qubit‐Efficient Quantum Local Search for Combinatorial Optimization." Advanced Quantum Technologies 9.3 (2026): e00438. 

[5] Raymond, Jack, et al. "Hybrid quantum annealing for larger-than-QPU lattice-structured problems." ACM Transactions on Quantum Computing 4.3 (2023): 1-30. 

[6] Barth, M. (2022). Quantum annealing for discrete optimization problems: From QUBO to hybrid algorithms (Doctoral dissertation, RWTH Aachen University). University Library of RWTH Aachen University. https://d-nb.info/1263925510/34 

- [7] Ceschini, A., Rosato, A., & Panella, M. (2025). Benchmarking quantum and hybrid algorithms on combinatorial optimization problems. arXiv. https://doi.org/10.48550/arXiv.2502.02245 

[8] COIN-OR Initiative. (2026). PuLP: A linear programming modeler written in Python (Version 2.8+) [Software documentation]. https://coin-or.github.io/pulp/ 

[9] Groetschel, M., Lovász, L., & Schrijver, A. (2019). Geometric algorithms and combinatorial optimization. arXiv preprint. https://arxiv.org/abs/1912.01759 

[10] Pelofske, J., Hahn, G., & Djidjev, H. (2022). Advanced hybrid quantum-classical algorithms for large scale combinatorial optimization. arXiv. https://doi.org/10.48550/arXiv.2202.03044 

[11] Pelofske, J., Hahn, G., & Djidjev, H. (2023). Quantum annealing algorithms for constrained optimization problems. arXiv. https://doi.org/10.48550/arXiv.2308.10765 

Anthropic. (2026). Claude (Büyük Dil Modeli) [Yazılım]. Erişim adresi: https://www.anthropic.com 

DeepSeek-AI. (2026). DeepSeek (Büyük Dil Modeli) [Yazılım]. Erişim adresi: https://www.deepseek.com 

Google. (2026). Gemini (Büyük Dil Modeli) [Yazılım]. Erişim adresi: <u>https://gemini.google.com</u> 

## **8. Yapay Zekâ Destek Beyanı:** 

Bu çalışmanın hazırlık, modelleme ve raporlama aşamalarında karşılaşılan teknik belirsizliklerin giderilmesi, akla takılan kavramsal/algoritmik soruların netleştirilmesi ve optimizasyon yöntemlerinin analiz edilmesi amacıyla üretken yapay zekâ araçlarından (Google Gemini, Anthropic Claude ve DeepSeek) destek alınmıştır. İlgili araçlar danışma ve fikir alışverişi amacıyla kullanılmış; elde edilen tüm teknik bilgiler, matematiksel modeller, sözde kodlar ve çözüm çıktıları yazarlar tarafından doğrulanarak rapor içeriğine dahil edilmiştir. 

