# Native quiz review

Status: pending fluent-speaker review.

Read each message and explanation. Mark an item approved only when its wording
is natural, its meaning is clear and the explanation supports the answer.
Report changes by language/item ID. No reviewer name is required. Record an
anonymous reviewer tag, language, IST date/time and the source revision below
when giving approval. Preserve answer keys unless the team agrees to a change.

Feedback received on 30 October was explicitly AI-assisted. The user reported
all answer keys correct and requested wording changes in hi/q2, hi/q5, hi/q9,
hi/q10, hinglish/q3 and hinglish/q9. Those edits are incorporated below. This
feedback does not constitute fluent-speaker approval of the 20 Hindi/Hinglish
items; a fluent reviewer must still read the edited messages and explanations.

These are labelled fictional examples. Domains and payment identifiers in the
quoted samples are examples to inspect, not links or instructions to follow.


## Hindi

Source: `seed/quiz/hi.json`, Git blob `e588f572925ba8aef86956196280e2daefbbff1b`.

Overall reviewer result: Pending.


### hi/q1

```text
(sample) 🔥 सिर्फ 7 दिन में पैसा डबल! 🔥
USDT में ₹10,000 लगाइए, अगले हफ्ते ₹20,000 पक्का वापस। हमारा AI ट्रेडिंग बॉट कभी लॉस नहीं करता 💯
ऑफर सिर्फ आज रात तक। जुड़ना है तो YES लिखिए, Telegram लिंक भेज देंगे।
```

Answer: **scam**.

सात दिन में पैसा 'पक्का' डबल करने की गारंटी कोई असली निवेश नहीं दे सकता, और कभी लॉस न करने वाला बॉट होता ही नहीं। किसी अनजान वॉलेट में भेजा गया क्रिप्टो आमतौर पर वापस नहीं मिलता।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q2

```text
(sample) प्रिय निवेशक, आपकी ₹1,500 की SIP (गंगा लार्ज कैप फंड - डायरेक्ट ग्रोथ, फोलियो XXXXXX3307) 10-11-2026 को आपके बैंक खाते XXXX5521 से ऑटो-डेबिट होगी। कृपया खाते में पर्याप्त बैलेंस रखें। - गंगा म्यूचुअल फंड
```

Answer: **genuine**.

यह असली SIP रिमाइंडर जैसा दिखता है: इसमें न कोई लिंक है, न पेमेंट की माँग, न OTP; पैसा उसी ऑटो-डेबिट मैंडेट से कटेगा जो आपने पहले से दिया है। फिर भी शक हो तो फ़ंड के आधिकारिक ऐप या स्टेटमेंट में अपनी SIP देख लें।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q3

```text
(sample) नमस्ते जी 🙏 आपको हमारे *VIP शेयर टिप्स* ग्रुप में जोड़ा गया है।
कल हमारे मेंबर्स ने एक ही कॉल में ₹2.5 लाख कमाए, ऊपर स्क्रीनशॉट देखिए 👆
रोज 3 पक्की कॉल, 95% एक्यूरेसी। फ्री में सीखने के लिए सर की असिस्टेंट से WhatsApp पर बात करें: 98XXXXXX21
```

Answer: **scam**.

बिना पूछे 'VIP' ग्रुप में जोड़ना और मुनाफ़े के स्क्रीनशॉट दिखाना वही तरीका है जिसके बारे में SEBI ने चेतावनी दी है; ऐसे स्क्रीनशॉट और 'मेंबर' अक्सर नकली होते हैं। 'पक्की कॉल' और 95% एक्यूरेसी का वादा कोई रजिस्टर्ड सलाहकार नहीं कर सकता।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q4

```text
(sample) बधाई हो! 🎉 आपके ट्रेडिंग अकाउंट में ₹4,86,200 का मुनाफा हुआ है।
पैसा निकालने से पहले 20% इनकम टैक्स (₹97,240) जमा करना जरूरी है, वरना अकाउंट फ्रीज हो जाएगा।
टैक्स इस UPI ID पर भेजें: taxclear.desk@paytm
```

Answer: **scam**.

शेयर के मुनाफ़े पर टैक्स आप ख़ुद अपने इनकम टैक्स रिटर्न में भरते हैं, किसी ऐप को पैसा निकालने से पहले नहीं। 'पहले टैक्स या फ़ीस भरो, तभी पैसा निकलेगा', ऐसी शर्त ही सबसे बड़ी खतरे की घंटी है।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q5

```text
(sample) प्रिय ग्राहक, 28-10-2026 के आपके ट्रेड का कॉन्ट्रैक्ट नोट आपके रजिस्टर्ड ईमेल पर भेज दिया गया है। PDF खोलने का पासवर्ड आपका PAN है (कैपिटल अक्षरों में)। कोई गड़बड़ी लगे तो ब्रोकर ऐप के हेल्प सेक्शन से संपर्क करें। - कावेरी स्टॉक ब्रोकिंग
```

Answer: **genuine**.

यह असली कॉन्ट्रैक्ट नोट की सूचना जैसा दिखता है: इसमें न लिंक है, न पेमेंट या OTP की माँग, सिर्फ़ ईमेल देखने को कहा गया है। फिर भी ब्रोकर के आधिकारिक ऐप में अपने ट्रेड मिलाकर देख लें।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q6

```text
(sample) Angel One के चुनिंदा ग्राहकों के लिए नया 'Angel One Elite' ऐप 🚀
इंस्टिट्यूशनल अकाउंट, ब्लॉक डील और जीरो ब्रोकरेज। ये सुविधाएं Play Store वाले ऐप में नहीं हैं, इसलिए यहीं से डाउनलोड करें:
https://angelone-elite.in/app
KYC सिर्फ 2 मिनट में।
```

Answer: **scam**.

Angel One की असली वेबसाइट angelone.in है; angelone-elite.in एक अलग डोमेन है जिसे असली जैसा दिखने के लिए बनाया गया है। असली ब्रोकर कभी Play Store या App Store छोड़कर किसी लिंक से ऐप डाउनलोड करने को नहीं कहते।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q7

```text
(sample) प्रिय ग्राहक, ट्रेडिंग अकाउंट में पैसे जोड़ने के लिए सिर्फ इस UPI ID पर भुगतान करें: kaveristock.brk@validicici (कावेरी स्टॉक ब्रोकिंग लि., SEBI रजि. नं. INZ000990017)। भुगतान से पहले यह UPI ID 'SEBI Check' पर जांच लें। WhatsApp पर आई किसी और UPI ID पर पैसे न भेजें।
```

Answer: **genuine**.

यह असली ब्रोकर का अनुरोध लगता है: UPI ID में SEBI वाला @valid हैंडल (@validicici) है, SEBI रजिस्ट्रेशन नंबर दिया है, और पहले जाँचने को कहा गया है। फिर भी भुगतान से पहले SEBI Check पर UPI ID मिला लें, और हो सके तो पैसे ब्रोकर के आधिकारिक ऐप से ही जोड़ें।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q8

```text
(sample) हेलो! घर बैठे पार्ट टाइम काम 🏠
बस YouTube वीडियो लाइक करें और ₹50 प्रति लाइक कमाएं, रोज ₹2,000-5,000 तक।
पहले 3 टास्क फ्री, पेमेंट तुरंत। उसके बाद 'प्रीपेड टास्क' में ₹1,000 लगाइए, ₹1,400 वापस पाइए।
शुरू करने के लिए YES लिखें।
```

Answer: **scam**.

कोई असली नौकरी काम देने के बदले आपसे पैसे नहीं माँगती। शुरुआत के छोटे पेमेंट भरोसा जीतने का चारा होते हैं; 'प्रीपेड टास्क' में रकम बढ़ती जाती है और फिर पैसे निकलना बंद हो जाता है।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q9

```text
(sample) नमस्ते, मैं SEBI रजिस्टर्ड रिसर्च एनालिस्ट हूं (रजि. नं. INH000990045)।
अगले हफ्ते खुलने वाले IPO में अपने इंस्टिट्यूशनल कोटे से आपको अलॉटमेंट दिलवा सकता हूं। एक लॉट ₹14,500 का है, पेमेंट इस UPI पर करें: ipoquota.desk@okaxis
स्लॉट सीमित हैं, आज ही कन्फर्म करें।
```

Answer: **scam**.

IPO में आवेदन सिर्फ़ आपके अपने ब्रोकर ऐप या बैंक से (ASBA या UPI मैंडेट) होता है और पैसा आपके ही खाते में ब्लॉक रहता है; किसी की UPI पर पैसे भेजने से अलॉटमेंट नहीं मिलता। मैसेज में लिखा रजिस्ट्रेशन नंबर कुछ साबित नहीं करता, SEBI की वेबसाइट पर नाम और नंबर दोनों मिलाएँ।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hi/q10

```text
(sample) 482913 आपके कार्ड XX4321 से BAZAARKART पर ₹3,999 के भुगतान का OTP है। यह 5 मिनट तक मान्य है। इसे किसी के साथ शेयर न करें, नर्मदा बैंक कभी OTP नहीं मांगता।
```

Answer: **genuine**.

यह आम बैंक OTP मैसेज है: इसमें कोई लिंक नहीं है और ख़ुद लिखा है कि OTP किसी को न बताएँ। अगर यह भुगतान आपने शुरू नहीं किया, तो OTP किसी को न दें, चाहे फ़ोन करने वाला ख़ुद को बैंक से बताए, और कार्ड के पीछे लिखे नंबर पर बैंक से बात करें।

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


## Hinglish

Source: `seed/quiz/hinglish.json`, Git blob `6f1a7b50fba0a1b0c0ab2cb9b1760ff5ea055b35`.

Overall reviewer result: Pending.


### hinglish/q1

```text
(sample) Bhai log 🔥 USDT me paisa DOUBLE sirf 7 din me, 100% guaranteed!!
₹10,000 daalo, next week ₹20,000 pakka. Mera AI bot kabhi loss nahi karta 💯
Offer sirf aaj raat tak, jaldi YES bhejo, Telegram link milega
```

Answer: **scam**.

7 din me paisa double ki 'guarantee' koi asli investment nahi de sakta, aur kabhi loss na karne wala bot hota hi nahi. Kisi anjaan wallet me bheja crypto aam taur pe wapas nahi aata.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q2

```text
(sample) *VIP Jackpot Calls* group me aapka swagat hai 🙏
Kal BANKNIFTY call me members ne ₹2.3 lakh kamaye, upar screenshots dekho 👆
Daily 3 sure shot calls, 95% accuracy. Seekhna bilkul free hai, Sir ki assistant se WhatsApp pe baat karo: 98XXXXXX21
```

Answer: **scam**.

Bina pooche 'VIP' group me add karna aur profit ke screenshots dikhana wahi tareeka hai jiske baare me SEBI ne warning di hai; aise screenshots aur 'members' aksar nakli hote hain. 'Sure shot' calls aur 95% accuracy ka waada koi registered adviser nahi kar sakta.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q3

```text
(sample) Kaveri Stock Broking: Aapke 28-Oct-2026 ke trades ka contract note aapke registered email pe bhej diya gaya hai. PDF ka password aapka PAN hai (capital letters me). Kuch galat lage toh app ke Help section se humse baat karein.
```

Answer: **genuine**.

Ye asli contract note ki notification jaisa lagta hai: na koi link, na payment, na OTP maanga gaya, sirf email check karne ko bola hai. Phir bhi broker ke official app me apne trades match kar lo.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q4

```text
(sample) Hello ji! Ghar baithe kamai ka mauka 💸
Google Maps pe hotels ko 5-star rating do, har task ₹150, roz ₹3,000 tak.
Pehle 3 task free aur payment turant UPI pe. Uske baad Telegram group me 'merchant task' milega: ₹2,000 deposit karo, ₹2,800 wapas.
Interested ho toh YES bhejo.
```

Answer: **scam**.

Koi asli job kaam dene ke badle aapse paise nahi maangti. Shuru ke chhote payments sirf bharosa jeetne ke liye hote hain; 'merchant task' ke deposit badhte jaate hain aur phir withdrawal ruk jaata hai.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q5

```text
(sample) Kaveri Stock Broking: Trading account me funds add karne ke liye sirf is UPI ID pe pay karein: kaveristock.brk@validhdfc (SEBI Reg. No. INZ000990017). Pay karne se pehle ye UPI ID 'SEBI Check' pe verify kar lein. WhatsApp pe aayi kisi aur UPI ID pe paise na bhejein.
```

Answer: **genuine**.

Ye asli broker ki request lagti hai: UPI ID me SEBI wala @valid handle (@validhdfc) hai, SEBI registration number diya hai, aur pehle verify karne ko kaha hai. Phir bhi pay karne se pehle SEBI Check pe UPI ID match karo, aur ho sake toh funds broker ke official app se hi add karo.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q6

```text
(sample) Dear client, SEBI ke naye rule ke hisaab se ab saare payments sirf verified 'valid' UPI ID pe honge ✅
Apna ₹25,000 margin top-up hamari verified ID pe bhejo: securetrade.valid@ybl (SEBI Reg. No. INZ000990088)
Aaj hi bhejo warna open positions square-off ho jayengi.
```

Answer: **scam**.

@ ke baad wala hissa dekho: ye ID @ybl pe khatam hoti hai, isliye ye SEBI ka @valid handle nahi hai, chahe naam me 'valid' likha ho. Message me likha registration number kuch saabit nahi karta; UPI ID SEBI Check pe aur number SEBI ki website pe milao.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q7

```text
(sample) Congratulations sir 🎉 Aapke account me ₹2,71,500 ka profit ho gaya hai.
Withdrawal se pehle 18% TDS + GST (₹48,870) bharna padega, warna account freeze ho jayega.
Tax yahan bhejo: tds.clearance@ibl
```

Answer: **scam**.

TDS aapke paise me se hi katta hai, kabhi alag se UPI pe nahi maanga jaata, aur share ke profit ka tax aap apne ITR me bharte ho. 'Pehle tax bharo, tabhi paisa niklega' ye shart hi sabse badi red flag hai.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q8

```text
(sample) 482913 is your OTP for a payment of Rs 3,999 at BAZAARKART using card XX4321. Valid for 5 minutes. Do NOT share this OTP with anyone. Narmada Bank never asks for your OTP.
```

Answer: **genuine**.

Ye normal bank OTP message hai: koi link nahi hai aur khud likha hai ki OTP kisi ko mat batao. Agar ye payment aapne shuru nahi kiya, toh OTP kisi ko mat do, chahe call karne wala khud ko bank ka bataye, aur card ke peeche likhe number pe bank ko call karo.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q9

```text
(sample) NSE: Trades executed on 28-Oct-2026 for PAN XXXXX1234X through your broker. Details have been sent to your registered email ID. If you have not done these trades, contact your broker immediately. -NSE
```

Answer: **genuine**.

Exchange aise SMS bhejta hai taaki aap check kar sako ki broker ne aapke PAN pe kaun se trades kiye: isme na link hai, na payment ki maang, na call karne ka number. Details apne registered email ya broker ke official app me dekho.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### hinglish/q10

```text
(sample) 🚨 IPO JACKPOT 🚨 Next week ke IPO me hamare institutional quota se 100% allotment pakka, listing pe 80% gain expected!
Ye quota sirf hamare VIP app me milta hai, Play Store pe nahi: https://groww-ipo-vip.in/app
Sirf 5 slots bache hain, jaldi karo!
```

Answer: **scam**.

Groww ki asli website groww.in hai; groww-ipo-vip.in alag domain hai, aur asli broker kabhi Play Store ke bahar se app install nahi karwate. Retail IPO me zyada demand hone pe allotment lottery se hota hai, isliye '100% allotment pakka' koi nahi dila sakta.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


## Marathi (optional)

Source: `seed/quiz/mr.json`, Git blob `7614f9b02afbec7da52e6c50d7e263041506611d`.

Overall reviewer result: Pending.


### mr/q1

```text
(sample) तुमच्या खाते क्र. XX4321 मधून 28-10-2026 रोजी UPI द्वारे 'साई किराणा स्टोअर्स' यांना ₹1,250 डेबिट झाले. हा व्यवहार तुम्ही केला नसेल तर कार्डच्या मागे दिलेल्या क्रमांकावर बँकेला कळवा. OTP, UPI PIN किंवा पासवर्ड कोणालाही सांगू नका. - नर्मदा बँक
```

Answer: **genuine**.

हा नेहमीसारखा बँकेचा डेबिट अलर्ट दिसतो: यात लिंक नाही, पैशांची मागणी नाही, उलट OTP कोणालाही न सांगण्याची आठवण आहे. व्यवहार तुमचा नसेल तर कार्डवर छापलेल्या क्रमांकावरच फोन करा, कोणी पाठवलेल्या नंबरवर नाही.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q2

```text
(sample) नमस्कार 🙏 तुम्हाला आमच्या *VIP शेअर टिप्स* ग्रुपमध्ये ॲड केलं आहे.
काल आमच्या मेंबर्सनी एकाच कॉलमध्ये ₹1.8 लाख कमावले, वरचे स्क्रीनशॉट बघा 👆
रोज 3 खात्रीशीर टिप्स. फ्री एंट्री फक्त आज रात्रीपर्यंत, लगेच जॉईन व्हा: chat.whatsapp.com/Lm4XqT7bRz2
```

Answer: **scam**.

न विचारता 'VIP' ग्रुपमध्ये ॲड करणे आणि नफ्याचे स्क्रीनशॉट दाखवणे, याच पद्धतीबद्दल SEBI ने इशारा दिला आहे; असे स्क्रीनशॉट आणि 'मेंबर्स' बहुतेक वेळा बनावट असतात. 'फक्त आज रात्रीपर्यंत' अशी घाई करायला लावणे हेही धोक्याचे लक्षण आहे.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q3

```text
(sample) सर/मॅडम, तुमचे Institutional Trading Account मंजूर झाले आहे ✅
अकाउंट ॲक्टिव्हेट करण्यासाठी किमान ₹50,000 भरावे लागतील. पेमेंट आमच्या डेस्कच्या UPI ID वर करा: alphadesk.7731@ybl
पेमेंट झाल्यावर स्क्रीनशॉट WhatsApp वर पाठवा.
```

Answer: **scam**.

SEBI नोंदणीकृत ब्रोकर UPI ने पैसे घेतात तेव्हा त्यांच्या ID मध्ये @valid हँडल (उदा. @validhdfc) असते, …@ybl सारखी वैयक्तिक ID नसते. सामान्य गुंतवणूकदाराला WhatsApp वर 'इन्स्टिट्यूशनल अकाउंट' देऊ करणे हे नेहमीचे आमिष आहे.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q4

```text
(sample) प्रिय ग्राहक, 28-10-2026 च्या तुमच्या व्यवहारांची कॉन्ट्रॅक्ट नोट तुमच्या नोंदणीकृत ईमेलवर पाठवली आहे. PDF उघडण्याचा पासवर्ड तुमचा PAN आहे (कॅपिटल अक्षरांत). काही शंका असल्यास ब्रोकरच्या ॲपमधील हेल्प विभागातून संपर्क करा. - कावेरी स्टॉक ब्रोकिंग
```

Answer: **genuine**.

ही खऱ्या कॉन्ट्रॅक्ट नोटची सूचना वाटते: यात लिंक, पैसे किंवा OTP काहीच मागितलेले नाही, फक्त ईमेल बघायला सांगितले आहे. तरीही तुमचे व्यवहार ब्रोकरच्या अधिकृत ॲपमध्ये जुळवून पाहा.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q5

```text
(sample) अभिनंदन! 🎉 तुमच्या ट्रेडिंग अकाउंटमध्ये ₹3,42,600 नफा जमा झाला आहे.
पैसे काढण्याआधी 15% कॅपिटल गेन टॅक्स (₹51,390) भरणे आवश्यक आहे, नाहीतर अकाउंट फ्रीझ होईल.
टॅक्स या UPI ID वर भरा: taxdesk.release@axl
```

Answer: **scam**.

शेअरच्या नफ्यावरचा टॅक्स तुम्ही स्वतः तुमच्या इन्कम टॅक्स रिटर्नमध्ये भरता, कोणत्याही ॲपला पैसे काढण्याआधी नाही. 'आधी टॅक्स किंवा फी भरा, मगच पैसे मिळतील' अशी अट हीच धोक्याची घंटा आहे.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q6

```text
(sample) Upstox Pro Max आता फक्त निवडक ग्राहकांसाठी 🎉
IPO प्री-अलॉटमेंट आणि ब्लॉक डील्स मिळवा. हे फीचर्स Play Store वरच्या ॲपमध्ये नाहीत, म्हणून ॲप इथून डाउनलोड करा:
https://upstox-promax.in/download
KYC फक्त 2 मिनिटांत.
```

Answer: **scam**.

Upstox ची खरी वेबसाइट upstox.com आहे; upstox-promax.in हे खऱ्यासारखे दिसणारे वेगळे डोमेन आहे. खरे ब्रोकर Play Store किंवा App Store सोडून लिंकवरून ॲप डाउनलोड करायला कधीच सांगत नाहीत.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q7

```text
(sample) NSE: तुमच्या PAN XXXXX1234X साठी 28-10-2026 रोजी तुमच्या ब्रोकरमार्फत झालेल्या व्यवहारांचा तपशील तुमच्या नोंदणीकृत ईमेलवर पाठवला आहे. हे व्यवहार तुम्ही केले नसतील तर लगेच तुमच्या ब्रोकरशी संपर्क करा. -NSE
```

Answer: **genuine**.

एक्सचेंज असे SMS पाठवते, जेणेकरून ब्रोकरने केलेले व्यवहार तुम्हाला जुळवता यावेत: यात लिंक नाही, पैशांची मागणी नाही, फोन करायला नंबरही नाही. तपशील तुमच्या नोंदणीकृत ईमेलमध्ये किंवा ब्रोकरच्या अधिकृत ॲपमध्ये बघा.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q8

```text
(sample) हॅलो! घरबसल्या पार्ट टाइम काम 🏠
फक्त YouTube व्हिडिओ लाईक करा आणि हॉटेलना रेटिंग द्या, प्रत्येक टास्कला ₹150, रोज ₹3,000 पर्यंत.
पहिले 3 टास्क फ्री आणि पेमेंट लगेच. त्यानंतर 'प्रीपेड टास्क' साठी ₹1,000 भरा, ₹1,300 परत मिळवा.
सुरू करायला YES लिहा.
```

Answer: **scam**.

कोणतीही खरी नोकरी काम देण्यासाठी तुमच्याकडून पैसे मागत नाही. सुरुवातीचे छोटे पेमेंट विश्वास जिंकण्यासाठी असतात; 'प्रीपेड टास्क' मध्ये रक्कम वाढत जाते आणि मग पैसे काढताच येत नाहीत.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q9

```text
(sample) प्रिय गुंतवणूकदार, तुमची ₹2,000 ची SIP (सह्याद्री फ्लेक्सी कॅप फंड, फोलिओ XXXXXX4821) 05-11-2026 रोजी तुमच्या बँक खात्यातून ऑटो-डेबिट होईल. कृपया खात्यात पुरेशी शिल्लक ठेवा. - सह्याद्री म्युच्युअल फंड
```

Answer: **genuine**.

हा खरा SIP रिमाइंडर दिसतो: यात लिंक, पेमेंटची मागणी किंवा OTP काहीच नाही; पैसे तुम्ही आधीच दिलेल्या मँडेटनेच कापले जातील. शंका असल्यास फंडच्या अधिकृत ॲपमध्ये किंवा स्टेटमेंटमध्ये SIP तपासा.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 


### mr/q10

```text
(sample) नमस्कार, आमचा 'USDT स्मार्ट प्लॅन' SEBI मान्यताप्राप्त आहे (नोंदणी क्र. INA000990031).
दर महिन्याला 8% निश्चित परतावा, म्हणजे वर्षभरात रक्कम दुप्पट.
ही ऑफर फक्त या महिन्यात सामील होणाऱ्यांसाठी. गुंतवणुकीसाठी आमच्या प्रतिनिधीला WhatsApp करा: 97XXXXXX40
```

Answer: **scam**.

क्रिप्टो किंवा USDT योजना SEBI कडे नोंदवल्या जात नाहीत, त्यामुळे 'SEBI मान्यताप्राप्त USDT प्लॅन' हा दावाच संशयास्पद आहे. मेसेजमधला नोंदणी क्रमांक काहीच सिद्ध करत नाही; SEBI च्या वेबसाइटवर नाव आणि क्रमांक दोन्ही जुळवा.

- [ ] Wording, meaning, answer and explanation approved by a fluent reviewer.

Suggested change or issue: 
