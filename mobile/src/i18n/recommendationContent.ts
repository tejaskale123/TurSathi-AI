import type { ClaudeGuidanceResponse } from '../config/recommendationApi';

export type Language = 'en' | 'mr' | 'hi';

export interface LocalizedRecommendation {
  isSeedTreatment: boolean;
  isHealthy: boolean;
  isVerified: boolean;
  isWebber?: boolean;
  diseaseExplanation: string;
  treatment: string;
  activeIngredient: string;
  recommendedQuantity: string;
  waterQuantity: string | null;
  perPumpQuantity: string | null;
  applicationTiming: string;
  applicationMethod: string;
  safetyPrecautions: string[];
  afterCareAdvisory: string[];
  importantAlert: string;
  farmerAction: string[];
  confidenceDisclaimer: string;
  headerTitle: string;
  guidanceSectionTitle: string;
  guidanceSectionSubtitle: string;
  afterSectionTitle: string;
  timingLabel: string;
  methodLabel: string;
}

interface DiseaseTranslationEntry {
  treatment: Record<Language, string>;
  activeIngredient: Record<Language, string>;
  recommendedQuantity: Record<Language, string>;
  waterQuantity: Record<Language, string | null>;
  perPumpQuantity: Record<Language, string | null>;
  sprayTiming: Record<Language, string>;
  applicationMethod: Record<Language, string>;
  safetyPrecautions: Record<Language, string[]>;
  afterCareAdvisory: Record<Language, string[]>;
  diseaseExplanation: Record<Language, string>;
  importantAlert: Record<Language, string>;
  farmerAction: Record<Language, string[]>;
}

const VERIFIED_DISEASE_DATA: Record<string, DiseaseTranslationEntry> = {
  Wilt: {
    treatment: {
      en: 'Trichoderma viride seed treatment — a biological agent that colonizes the root zone and provides protection against Fusarium udum.',
      mr: 'ट्रायकोडर्मा व्हिरिडी (Trichoderma viride) जैविक बियाणे प्रक्रिया — मुळांच्या भागाचे संरक्षण करणारा आणि फ्युजॅरियम विल्टपासून बचाव करणारा जैविक घटक.',
      hi: 'ट्राइकोडर्मा विरिडी (Trichoderma viride) जैविक बीज उपचार — जड़ क्षेत्र की रक्षा करने वाला और फ्यूजेरियम उकठा से बचाव करने वाला जैविक घटक।',
    },
    activeIngredient: {
      en: 'Trichoderma viride 1% WP (biological fungicide / biocontrol agent)',
      mr: 'ट्रायकोडर्मा व्हिरिडी १% डब्ल्यूपी (Trichoderma viride 1% WP - जैविक बुरशीनाशक / नियंत्रण घटक)',
      hi: 'ट्राइकोडर्मा विरिडी 1% WP (Trichoderma viride 1% WP - जैविक कवकनाशी)',
    },
    recommendedQuantity: {
      en: '10 g per kg of seed',
      mr: '१० ग्रॅम प्रति किलो बियाणे',
      hi: '10 ग्राम प्रति किलोग्राम बीज',
    },
    waterQuantity: {
      en: null,
      mr: null,
      hi: null,
    },
    perPumpQuantity: {
      en: null,
      mr: null,
      hi: null,
    },
    sprayTiming: {
      en: 'Apply as seed treatment before sowing. If also applying Rhizobium culture, apply Trichoderma first, allow seeds to shade-dry for ~2 hours, then apply Rhizobium.',
      mr: 'पेरणीपूर्वी बियाणे प्रक्रिया म्हणून वापरावे. रायझोबियम जिवाणू संवर्धन वापरत असल्यास, आधी ट्रायकोडर्मा चोळावे, बियाणे २ तास सावलीत सुकवून मग रायझोबियम लावावे.',
      hi: 'बुवाई से पहले बीज उपचार के रूप में उपयोग करें। यदि राइजोबियम कल्चर का उपयोग कर रहे हैं, तो पहले ट्राइकोडर्मा लगाएं, 2 घंटे छाया में सुखाएं, फिर राइजोबियम लगाएं।',
    },
    applicationMethod: {
      en: 'Seed treatment (biological). This is NOT a foliar spray. Mix the required quantity of Trichoderma viride uniformly with seeds. Shade-dry for ~2 hours before sowing. Optionally combine with soil application: mix 2.5 kg Trichoderma viride/ha with 50 kg well-decomposed FYM and apply to soil before sowing.',
      mr: 'बियाणे प्रक्रिया (जैविक). ही पानांवरील फवारणी नाही. ट्रायकोडर्माची आवश्यक मात्रा बियाण्याला एकसमान चोळावी. पेरणीपूर्वी २ तास सावलीत वाळवावे. ऐच्छिक जमीन वापर: २.५ किलो ट्रायकोडर्मा प्रति हेक्टरी ५० किलो चांगल्या कुजलेल्या शेणखतात मिसळून पेरणीपूर्वी जमिनीत द्यावे.',
      hi: 'बीज उपचार (जैविक)। यह पत्तियों पर छिड़काव नहीं है। ट्राइकोडर्मा की आवश्यक मात्रा बीजों में समान रूप से मिलाएं। बुवाई से पहले 2 घंटे छाया में सुखाएं। वैकल्पिक मृदा उपयोग: 2.5 किग्रा ट्राइकोडर्मा प्रति हेक्टेयर 50 किग्रा सड़े गोबर की खाद में मिलाकर बुवाई पूर्व मिट्टी में दें।',
    },
    safetyPrecautions: {
      en: [
        'Avoid exposure to direct sunlight after treating seeds as it reduces bioagent viability.',
        'Do not mix with chemical fungicides unless compatibility is confirmed.',
        'Wash hands thoroughly with soap after handling treated seeds.',
        'Store treated seeds in a cool, shaded place away from moisture.',
      ],
      mr: [
        'बियाणे प्रक्रियेनंतर थेट उन्हात ठेवू नका, यामुळे जैविक घटकांची कार्यक्षमता कमी होते.',
        'सुसंगततेची खात्री असल्याशिवाय रासायनिक बुरशीनाशकांसोबत मिसळू नका.',
        'बियाणे हाताळल्यानंतर हात साबणाने स्वच्छ धुवा.',
        'प्रक्रिया केलेले बियाणे सावलीत आणि कोरड्या जागी सुरक्षित साठवा.',
      ],
      hi: [
        'बीज उपचार के बाद सीधी धूप में न रखें, इससे जैविक घटक की प्रभावशीलता कम होती है।',
        'रासायनिक कवकनाशी के साथ तब तक न मिलाएं जब तक संगतता की पुष्टि न हो।',
        'बीज संभालने के बाद हाथ साबुन से अच्छी तरह धोएं।',
        'उपचारित बीजों को छायादार और सूखी जगह पर रखें।',
      ],
    },
    afterCareAdvisory: {
      en: [
        'Uproot and remove wilted plants from the field to reduce inoculum.',
        'Practice crop rotation — avoid growing pigeonpea in the same field for at least 3 years in wilt-affected areas.',
        'Monitor the crop and consult your local Krishi Vigyan Kendra (KVK) for region-specific follow-up. Source: ICAR-IIPR, Kanpur.',
      ],
      mr: [
        'रोगाचा प्रादुर्भाव कमी करण्यासाठी वाळलेली/मर झालेली झाडे शेतातून उपटून नष्ट करा.',
        'पीक फेरपालट करा — विल्ट बाधित शेतात सलग ३ वर्षे तूर घेणे टाळा.',
        'पिकाचे नियमित निरीक्षण करा आणि स्थानिक कृषी विज्ञान केंद्र (KVK) चा सल्ला घ्या. स्रोत: ICAR-IIPR, कानपूर.',
      ],
      hi: [
        'उकठा प्रभावित सूखे पौधों को उखाड़कर नष्ट करें ताकि संक्रमण न फैले।',
        'फसल चक्र अपनाएं — उकठा प्रभावित खेतों में कम से कम 3 साल तक तूर न लगाएं।',
        'फसल की निगरानी करें और स्थानीय कृषि विज्ञान केंद्र (KVK) से संपर्क करें। स्रोत: ICAR-IIPR, कानपुर।',
      ],
    },
    diseaseExplanation: {
      en: 'Fusarium wilt (Fusarium udum) is a serious soil-borne fungal disease of pigeonpea. Infected plants show yellowing, wilting, and drying. The pathogen attacks the root vascular system.',
      mr: 'फ्युजॅरियम विल्ट (फ्युजॅरियम उडम) हा तुरीचा एक गंभीर जमिनीतून पसरणारा बुरशीजन्य रोग आहे. बाधित झाडांची पाने पिवळी पडतात, सुकतात आणि झाड वाळते. हा रोग मुळांवर परिणाम करतो.',
      hi: 'फ्यूजेरियम उकठा (Fusarium udum) तूर की एक गंभीर मृदा जनित फफूंद जनित बीमारी है। संक्रमित पौधों में पीलापन, मुरझाना और सूखना देखा जाता है। यह बीमारी जड़ों को प्रभावित करती है।',
    },
    importantAlert: {
      en: 'SEED TREATMENT ONLY — Apply to seeds before sowing or to soil. Do NOT spray on standing crop foliage.',
      mr: 'फक्त बियाणे / जमीन उपचार — पेरणीपूर्वी बियाण्यावर किंवा जमिनीत वापरावे. उभ्या पिकाच्या पानांवर फवारणी करू नका.',
      hi: 'केवल बीज / मृदा उपचार — बुवाई से पहले बीजों पर या मिट्टी में उपयोग करें। खड़ी फसल की पत्तियों पर छिड़काव न करें।',
    },
    farmerAction: {
      en: [
        'Use certified wilt-resistant pigeonpea varieties (e.g., Asha, Maruti) for future plantings.',
        'Apply Trichoderma viride seed treatment before sowing.',
        'Uproot and burn diseased plants to avoid disease build-up in soil.',
      ],
      mr: [
        'पुढील लागवडीसाठी मर-रोग प्रतिकारक प्रमाणित वाणांचा (उदा. आशा, मारुती) वापर करा.',
        'पेरणीपूर्वी ट्रायकोडर्मा व्हिरिडी बियाणे प्रक्रिया अवश्य करा.',
        'जमिनीत बुरशीचा संसर्ग वाढू नये म्हणून बाधित वाळलेली झाडे उपटून नष्ट करा.',
      ],
      hi: [
        'अगली बुवाई के लिए उकठा-प्रतिरोधी प्रमाणित किस्मों (जैसे आशा, मारुति) का चयन करें।',
        'बुवाई से पहले ट्राइकोडर्मा विरिडी बीज उपचार अवश्य करें।',
        'मिट्टी में फफूंद का प्रसार रोकने के लिए प्रभावित सूखे पौधों को उखाड़कर नष्ट करें।',
      ],
    },
  },

  Leaf_Spot: {
    treatment: {
      en: 'Mancozeb 75 WP foliar spray',
      mr: 'मॅनकोझेब ७५ डब्ल्यूपी (Mancozeb 75 WP) पानांवर फवारणी',
      hi: 'मैनकोजेब 75 WP (Mancozeb 75 WP) पत्तियों पर छिड़काव',
    },
    activeIngredient: {
      en: 'Mancozeb 75% WP',
      mr: 'मॅनकोझेब ७५% डब्ल्यूपी (Mancozeb 75% WP)',
      hi: 'मैनकोजेब 75% WP',
    },
    recommendedQuantity: {
      en: '2.5 g per litre of water',
      mr: '२.५ ग्रॅम प्रति लिटर पाणी (३७.५ ग्रॅम प्रति १५ लिटर पंप)',
      hi: '2.5 ग्राम प्रति लीटर पानी (37.5 ग्राम प्रति 15 लीटर पंप)',
    },
    waterQuantity: {
      en: '500 L/ha (adequate coverage)',
      mr: '५०० लिटर प्रति हेक्टरी (एकसमान कव्हरेजसाठी)',
      hi: '500 लीटर प्रति हेक्टेयर (समान छिड़काव हेतु)',
    },
    perPumpQuantity: {
      en: '37.5 g per 15-litre pump',
      mr: '३७.५ ग्रॅम प्रति १५ लिटर पंप',
      hi: '37.5 ग्राम प्रति 15 लीटर पंप',
    },
    sprayTiming: {
      en: 'At the onset of leaf spot symptoms; repeat after 10-14 days if wet weather continues. Follow label instructions.',
      mr: 'पानांवर ठिपके दिसू लागताच फवारणी करा; दमट हवामान राहिल्यास १०-१४ दिवसांनी पुन्हा फवारणी करा. लेबलच्या सूचना पाळा.',
      hi: 'पत्तियों पर धब्बे दिखते ही छिड़काव करें; यदि मौसम नम रहे तो 10-14 दिन बाद पुनः छिड़काव करें। लेबल का पालन करें।',
    },
    applicationMethod: {
      en: 'Foliar spray using a calibrated hollow-cone nozzle. Cover upper and lower leaf surfaces evenly.',
      mr: 'पानांवर एकसमान फवारणी. पानांच्या वरच्या आणि खालच्या दोन्ही भागांवर व्यवस्थित औषध पोहोचेल याची खात्री करा.',
      hi: 'पत्तियों पर एकसमान छिड़काव। पत्तियों की ऊपरी और निचली दोनों सतहों पर अच्छी तरह दवा पहुंचे।',
    },
    safetyPrecautions: {
      en: [
        'Wear protective mask, gloves, and protective clothing during spraying.',
        'Do not spray against the wind direction.',
        'Keep children and livestock away from sprayed field.',
        'Observe pre-harvest interval according to product label.',
      ],
      mr: [
        'फवारणी करताना मास्क, हातमोजे आणि संरक्षक कपडे वापरा.',
        'वाऱ्याच्या विरुद्ध दिशेने फवारणी करू नका.',
        'फवारणी केलेल्या क्षेत्रापासून लहान मुले आणि जनावरांना दूर ठेवा.',
        'उत्पादन लेबलवरील काढणीपूर्वीचा सुरक्षित कालावधी (PHI) पाळा.',
      ],
      hi: [
        'छिड़काव के समय मास्क, दस्ताने और सुरक्षात्मक कपड़े पहनें।',
        'हवा की विपरीत दिशा में छिड़काव न करें।',
        'छिड़काव वाले खेत से बच्चों और मवेशियों को दूर रखें।',
        'उत्पाद लेबल पर दिए गए तुड़ाई पूर्व सुरक्षित समय (PHI) का पालन करें।',
      ],
    },
    afterCareAdvisory: {
      en: [
        'Clean spraying equipment thoroughly with fresh water after use.',
        'Wash hands and face with soap after handling chemicals.',
        'Dispose of empty pesticide containers safely as per agricultural norms.',
      ],
      mr: [
        'वापरानंतर फवारणी पंप स्वच्छ पाण्याने चांगला धुवा.',
        'औषध हाताळल्यानंतर हात आणि चेहरा साबणाने स्वच्छ धुवा.',
        'रिकाम्या बाटल्या आणि पाकिटांची विल्हेवाट नियमांनुसार सुरक्षित लावा.',
      ],
      hi: [
        'उपयोग के बाद छिड़काव पंप को साफ पानी से अच्छी तरह धोएं।',
        'कीटनाशक के संपर्क के बाद हाथ और मुंह साबुन से अच्छी तरह धोएं।',
        'खाली डिब्बों और पैकेटों का सुरक्षित निपटान करें।',
      ],
    },
    diseaseExplanation: {
      en: 'Tur Leaf Spot causes brown or dark necrotic lesions on the leaves, leading to premature leaf drop and reduced crop yield.',
      mr: 'तूर पानांवरील ठिपके रोगामुळे पानांवर तपकिरी किंवा काळे डाग पडतात, ज्यामुळे पाने गळतात आणि उत्पादनात घट होते.',
      hi: 'तूर पत्ती धब्बा रोग के कारण पत्तियों पर भूरे या काले धब्बे पड़ते हैं, जिससे पत्तियां समय से पहले गिर सकती हैं।',
    },
    importantAlert: {
      en: 'FOLIAR SPRAY ONLY — Apply evenly to crop canopy using clean water and calibrated sprayer.',
      mr: 'फक्त पानांवर फवारणी — स्वच्छ पाणी आणि योग्य पंपाचा वापर करून पिकावर एकसमान फवारणी करा.',
      hi: 'केवल पत्तियों पर छिड़काव — साफ पानी और सही पंप का उपयोग करके फसल पर समान रूप से छिड़काव करें।',
    },
    farmerAction: {
      en: [
        'Inspect leaves weekly for symptom spread.',
        'Ensure proper plant spacing for good aeration.',
        'Apply recommended fungicide if leaf spots spread.',
      ],
      mr: [
        'रोगाचा प्रसार तपासण्यासाठी आठवड्यातून एकदा शेताची पाहणी करा.',
        'हवा खेळती राहण्यासाठी योग्य अंतर ठेवा.',
        'डाग वाढत असल्यास शिफारस केलेले बुरशीनाशक फवारा.',
      ],
      hi: [
        'रोग के फैलाव की जांच के लिए सप्ताह में एक बार खेत का निरीक्षण करें।',
        'हवा के संचलन के लिए उचित दूरी बनाए रखें।',
        'धब्बे बढ़ने पर अनुशंसित कवकनाशी का छिड़काव करें।',
      ],
    },
  },

  Sterilic_mosaic: {
    treatment: {
      en: 'Fenazaquin 10 EC foliar spray (acaricide against eriophyid mite vector)',
      mr: 'फेनाझाक्विन १० ईसी (Fenazaquin 10 EC) पानांवर फवारणी (कोळी कीड नियंत्रक)',
      hi: 'फेनाजाक्विन 10 EC (Fenazaquin 10 EC) पत्तियों पर छिड़काव (माइट नियंत्रण)',
    },
    activeIngredient: {
      en: 'Fenazaquin 10% EC',
      mr: 'फेनाझाक्विन १०% ईसी (Fenazaquin 10% EC)',
      hi: 'फेनाजाक्विन 10% EC',
    },
    recommendedQuantity: {
      en: '2 ml per litre of water',
      mr: '२ मिली प्रति लिटर पाणी (३० मिली प्रति १५ लिटर पंप)',
      hi: '2 मिली प्रति लीटर पानी (30 मिली प्रति 15 लीटर पंप)',
    },
    waterQuantity: {
      en: '500 L/ha (sufficient canopy wetting)',
      mr: '५०० लिटर प्रति हेक्टरी (झाडे व्यवस्थित भिजण्यासाठी)',
      hi: '500 लीटर प्रति हेक्टेयर (पौधों को अच्छी तरह भिगोने हेतु)',
    },
    perPumpQuantity: {
      en: '30 ml per 15-litre pump',
      mr: '३० मिली प्रति १५ लिटर पंप',
      hi: '30 मिली प्रति 15 लीटर पंप',
    },
    sprayTiming: {
      en: 'Spray soon after appearance of mite vector or initial mosaic symptoms; repeat after 15 days if necessary.',
      mr: 'कोळी कीड किंवा वांझ रोगाची सुरुवातीची लक्षणे दिसताच फवारणी करा; आवश्यक असल्यास १५ दिवसांनी पुन्हा फवारणी करा.',
      hi: 'माइट या बांझपन रोग के शुरुआती लक्षण दिखते ही छिड़काव करें; आवश्यकता पड़ने पर 15 दिन बाद दोबारा छिड़काव करें।',
    },
    applicationMethod: {
      en: 'Foliar spray focusing on the lower leaf surfaces where eriophyid mites reside.',
      mr: 'पानांवर फवारणी — प्रामुख्याने पानांच्या खालच्या बाजूवर लक्ष केंद्रित करा जिथे सूक्ष्म कोळी कीड राहते.',
      hi: 'पत्तियों पर छिड़काव — विशेष रूप से पत्तियों की निचली सतह पर ध्यान दें जहां माइट कीड़े रहते हैं।',
    },
    safetyPrecautions: {
      en: [
        'Wear protective gear including gloves and face mask.',
        'Avoid spraying during high temperatures or strong wind.',
        'Keep animals and bees away during and immediately after spraying.',
      ],
      mr: [
        'हातमोजे आणि फेस मास्कसह सर्व संरक्षक साधने वापरा.',
        'दुपारी तीव्र उन्हात किंवा जोरदार वाऱ्याच्या वेळी फवारणी करू नका.',
        'फवारणीच्या वेळी पाळीव जनावरांना शेतापासून दूर ठेवा.',
      ],
      hi: [
        'दस्ताने और फेस मास्क सहित सुरक्षात्मक उपकरण पहनें।',
        'तेज धूप या तेज हवा के दौरान छिड़काव न करें।',
        'छिड़काव के समय पशुओं को खेत से दूर रखें।',
      ],
    },
    afterCareAdvisory: {
      en: [
        'Wash all equipment and clothing thoroughly after application.',
        'Rogue out and destroy severely stunted plants to limit disease transmission.',
        'Consult local agricultural officer if symptoms persist.',
      ],
      mr: [
        'फवारणीनंतर कपडे आणि पंप साबणाने स्वच्छ धुवा.',
        'रोगाचा प्रसार रोखण्यासाठी तीव्र प्रादुर्भाव झालेली वांझ झाडे उपटून नष्ट करा.',
        'लक्षणे कायम राहिल्यास स्थानिक कृषी अधिकाऱ्यांचा सल्ला घ्या.',
      ],
      hi: [
        'छिड़काव के बाद उपकरण और कपड़े अच्छी तरह धोएं।',
        'संक्रमण रोकने के लिए गंभीर रूप से प्रभावित पौधों को उखाड़कर नष्ट करें।',
        'लक्षण बने रहने पर स्थानीय कृषि अधिकारी से संपर्क करें।',
      ],
    },
    diseaseExplanation: {
      en: 'Sterility Mosaic Disease is caused by a virus transmitted by eriophyid mites (Aceria cajani). Plants become bushy, leaves remain small, and flowering is severely suppressed.',
      mr: 'तूर वांझ रोग (स्टेरिलिटी मोझॅक) हा सूक्ष्म कोळी (Eriophyid mite) किडीमुळे पसरतो. झाडे झुडपासारखी होतात, पाने लहान राहतात आणि फुले-शेंगा लागत नाहीत.',
      hi: 'तूर बांझपन मोज़ेक रोग बारीक मकड़ी (माइट) द्वारा फैलता है। पौधे झाड़ीदार हो जाते हैं, पत्तियां छोटी रह जाती हैं और फूल-फलियां नहीं आतीं।',
    },
    importantAlert: {
      en: 'TARGET THE MITE VECTOR — Apply acaricide to lower leaf surfaces where vector mites shelter.',
      mr: 'कोळी किडीचे नियंत्रण करा — कीटकनाशकाची फवारणी प्रामुख्याने पानांच्या खालच्या बाजूवर करावी.',
      hi: 'माइट कीट पर नियंत्रण करें — छिड़काव मुख्य रूप से पत्तियों की निचली सतह पर करें।',
    },
    farmerAction: {
      en: [
        'Inspect underside of leaves using a hand lens for tiny eriophyid mites.',
        'Remove severely infected bushy plants from the plot.',
        'Spray recommended acaricide to control vectors.',
      ],
      mr: [
        'पानांच्या खालच्या बाजूची बारीक कोळी किडीसाठी पाहणी करा.',
        'तीव्र बाधित झुडपे शेतातून उपटून नष्ट करा.',
        'कोळी नियंत्रणासाठी शिफारस केलेली फवारणी वेळेवर करा.',
      ],
      hi: [
        'पत्तियों की निचली सतह की जांच करें।',
        'अत्यधिक प्रभावित पौधों को खेत से हटा दें।',
        'माइट नियंत्रण के लिए अनुशंसित कीटनाशक का छिड़काव करें।',
      ],
    },
  },

  Healthy: {
    treatment: {
      en: 'No chemical spray required. Continue regular crop monitoring.',
      mr: 'कोणत्याही रासायनिक फवारणीची आवश्यकता नाही. नियमित पीक निरीक्षण चालू ठेवा.',
      hi: 'किसी रासायनिक छिड़काव की आवश्यकता नहीं है। नियमित फसल निरीक्षण जारी रखें।',
    },
    activeIngredient: {
      en: 'Not applicable (healthy leaf)',
      mr: 'लागू नाही (निरोगी पान)',
      hi: 'लागू नहीं (स्वस्थ पत्ती)',
    },
    recommendedQuantity: {
      en: 'Not applicable',
      mr: 'लागू नाही',
      hi: 'लागू नहीं',
    },
    waterQuantity: {
      en: null,
      mr: null,
      hi: null,
    },
    perPumpQuantity: {
      en: null,
      mr: null,
      hi: null,
    },
    sprayTiming: {
      en: 'Not applicable — regular monitoring twice a week.',
      mr: 'लागू नाही — आठवड्यातून दोनदा नियमित शेत पाहणी करा.',
      hi: 'लागू नहीं — सप्ताह में दो बार नियमित खेत निरीक्षण करें।',
    },
    applicationMethod: {
      en: 'Not applicable — do not spray healthy foliage.',
      mr: 'लागू नाही — निरोगी पानांवर फवारणी करू नका.',
      hi: 'लागू नहीं — स्वस्थ पत्तियों पर छिड़काव न करें।',
    },
    safetyPrecautions: {
      en: [
        'Avoid using unnecessary chemical pesticides on healthy crops.',
        'Protect beneficial insects and pollinators (bees, ladybird beetles) in the field.',
        'Maintain balanced fertilizer and optimal irrigation management.',
      ],
      mr: [
        'निरोगी पिकावर अनावश्यक रासायनिक कीटकनाशकांचा वापर टाळा.',
        'शेतात मित्रकीटकांचे (उदा. मधमाश्या, लेडीबर्ड बीटल) संवर्धन करा.',
        'संतुलित खत आणि पाणी व्यवस्थापन राखा.',
      ],
      hi: [
        'स्वस्थ फसल पर अनावश्यक रासायनिक कीटनाशकों के प्रयोग से बचें।',
        'खेत में मित्र कीटों (जैसे मधुमक्खियां, लेडीबर्ड बीटल) का संरक्षण करें।',
        'संतुलित खाद और पानी प्रबंधन बनाए रखें।',
      ],
    },
    afterCareAdvisory: {
      en: [
        'Continue regular field inspection twice a week.',
        'Keep the field clean and weed-free to prevent pest harborage.',
        'If any symptoms appear on fresh leaves or pods, scan again.',
      ],
      mr: [
        'आठवड्यातून दोनदा शेताची नियमित पाहणी करत राहा.',
        'शेत तणमुक्त आणि स्वच्छ ठेवा जेणेकरून किडींचा प्रादुर्भाव होणार नाही.',
        'पानांवर किंवा शेंगांवर नवीन लक्षणे दिसल्यास पुन्हा स्कॅन करा.',
      ],
      hi: [
        'सप्ताह में दो बार खेत का नियमित निरीक्षण जारी रखें।',
        'खेत को खरपतवार मुक्त और साफ रखें।',
        'पत्तियों या फलियों पर नए लक्षण दिखने पर दोबारा स्कैन करें।',
      ],
    },
    diseaseExplanation: {
      en: 'The Tur leaf appears healthy with no visual symptoms of Leaf Spot, Sterility Mosaic, or Leaf Webber detected.',
      mr: 'तुरीचे पान निरोगी दिसत असून पानावर टिपके, वांझ रोग किंवा पानावरील आळीची कोणतीही लक्षणे आढळलेली नाहीत.',
      hi: 'अरहर की पत्ती स्वस्थ दिखाई दे रही है और इस पर कोई रोग का लक्षण नहीं मिला है।',
    },
    importantAlert: {
      en: 'HEALTHY CROP — NO chemical spray required. Avoid unnecessary pesticide applications.',
      mr: 'निरोगी पीक — कोणत्याही रासायनिक फवारणीची गरज नाही. अनावश्यक औषध फवारणी टाळा.',
      hi: 'स्वस्थ फसल — किसी रासायनिक छिड़काव की आवश्यकता नहीं है। अनावश्यक दवा छिड़काव से बचें।',
    },
    farmerAction: {
      en: [
        'Continue regular field monitoring twice a week.',
        'Maintain optimal irrigation and balanced fertilization.',
        'Keep the field clean and weed-free to prevent pest harborage.',
      ],
      mr: [
        'आठवड्यातून दोनदा शेताची नियमित पाहणी करत राहा.',
        'योग्य पाणी व्यवस्थापन व संतुलित खतमात्रा द्या.',
        'कीड व रोगाचा प्रादुर्भाव टाळण्यासाठी शेत तणमुक्त व स्वच्छ ठेवा.',
      ],
      hi: [
        'सप्ताह में दो बार खेत का नियमित निरीक्षण जारी रखें।',
        'उचित सिंचाई और संतुलित उर्वरक प्रबंधन बनाए रखें।',
        'खरपतवार नियंत्रण रखें ताकि कीटों का प्रसार न हो।',
      ],
    },
  },

  Leaf_webber: {
    treatment: {
      en: 'No verified chemical spray recommended. Practice cultural and manual control.',
      mr: 'कोणत्याही प्रमाणित रासायनिक फवारणीची शिफारस नाही. एकात्मिक व भौतिक पद्धतींचा वापर करा.',
      hi: 'किसी सत्यापित रासायनिक छिड़काव की सिफारिश नहीं है। एकीकृत और भौतिक तरीकों का उपयोग करें।',
    },
    activeIngredient: {
      en: 'Not applicable (no verified chemical recommendation)',
      mr: 'लागू नाही (प्रमाणित रासायनिक शिफारस नाही)',
      hi: 'लागू नहीं (सत्यापित रासायनिक सिफारिश नहीं)',
    },
    recommendedQuantity: {
      en: 'Not applicable',
      mr: 'लागू नाही',
      hi: 'लागू नहीं',
    },
    waterQuantity: {
      en: null,
      mr: null,
      hi: null,
    },
    perPumpQuantity: {
      en: null,
      mr: null,
      hi: null,
    },
    sprayTiming: {
      en: 'Not applicable — regular field monitoring of shoot tips.',
      mr: 'लागू नाही — शेंड्याकडील पानांचे नियमित निरीक्षण करा.',
      hi: 'लागू नहीं — शीर्ष पत्तियों का नियमित निरीक्षण करें।',
    },
    applicationMethod: {
      en: 'Manual collection / Cultural management. Do not apply unverified chemical sprays.',
      mr: 'भौतिक नियंत्रण / जाळी झालेली पाने तोडून नष्ट करणे. अनधिकृत रासायनिक फवारणी करू नका.',
      hi: 'भौतिक नियंत्रण / जाले वाली पत्तियों को तोड़कर नष्ट करना। अनधिकृत रासायनिक छिड़काव न करें।',
    },
    safetyPrecautions: {
      en: [
        'Do not use unverified or banned chemical pesticides (such as Dichlorvos).',
        'Protect beneficial insects, spiders, and parasitoids in the field.',
        'Consult your local Krishi Vigyan Kendra (KVK) or agricultural extension officer for approved safe management.',
      ],
      mr: [
        'अनधिकृत किंवा बंदी घातलेली रासायनिक कीटकनाशके (उदा. डायक्लोर्व्हॉस) वापरू नका.',
        'शेतातील मित्रकीटक, कोळी आणि परोपजीवी कीटकांचे संवर्धन करा.',
        'सध्याच्या अधिकृत व सुरक्षित कीड नियंत्रण उपायांसाठी स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी अधिकाऱ्यांचा सल्ला घ्या.',
      ],
      hi: [
        'अनधिकृत या प्रतिबंधित रासायनिक कीटनाशकों (जैसे डाइक्लोरवोस) का उपयोग न करें।',
        'खेत में मित्र कीटों और मकड़ियों का संरक्षण करें।',
        'वर्तमान में स्वीकृत सुरक्षित प्रबंधन उपायों के लिए स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।',
      ],
    },
    afterCareAdvisory: {
      en: [
        'Inspect shoot tips and webbed leaf clusters regularly in the field.',
        'Manually collect and destroy folded/webbed leaves containing larvae in early infestation.',
        'Observe the crop closely and consult KVK if pest infestation spreads.',
      ],
      mr: [
        'शेंड्याकडील पाने आणि जाळी बांधलेल्या पानांचे शेतात नियमित निरीक्षण करा.',
        'सुरुवातीच्या काळात जाळी झालेली पाने अळीसह गोळा करून नष्ट करा.',
        'पिकाचे बारीक निरीक्षण करा आणि प्रादुर्भाव वाढल्यास कृषी विज्ञान केंद्राचा (KVK) सल्ला घ्या.',
      ],
      hi: [
        'शीर्ष पत्तियों और जाले वाले गुच्छों का खेत में नियमित निरीक्षण करें।',
        'शुरुआती अवस्था में जाले वाली पत्तियों को इल्ली सहित इकट्ठा कर नष्ट करें।',
        'फसल की नियमित निगरानी करें और प्रसार होने पर केवीके (KVK) से परामर्श लें।',
      ],
    },
    diseaseExplanation: {
      en: 'Leaf Webber (Grapholita critica) is a lepidopteran pest of pigeonpea where larvae web top leaves together and feed inside. Verified chemical spray guidance is currently unavailable for Leaf Webber. Do not apply unauthorized or banned chemicals.',
      mr: 'पाने गुंडाळणारी अळी (Leaf webber / Grapholita critica) ही तुरीवरील कीड असून अळ्या शेंड्याची पाने जाळ्याने एकत्र बांधून आतून खातात. या किडीसाठी प्रमाणित रासायनिक फवारणी मार्गदर्शन सध्या उपलब्ध नाही. अनधिकृत किंवा बंदी घातलेली कीटकनाशके वापरू नका.',
      hi: 'लीफ वेबर (Grapholita critica) तूर की एक कीट है जिसकी इल्लियां शीर्ष पत्तियों को आपस में जाले से बांधकर अंदर खाती हैं। इस कीट के लिए सत्यापित रासायनिक छिड़काव मार्गदर्शन वर्तमान में उपलब्ध नहीं है। अनधिकृत या प्रतिबंधित रसायनों का उपयोग न करें।',
    },
    importantAlert: {
      en: 'SAFE ADVISORY ONLY — Chemical spray guidance is UNVERIFIED for Leaf Webber. Do NOT apply unverified or banned pesticides.',
      mr: 'महत्त्वाची सूचना: पाने गुंडाळणाऱ्या अळीसाठी कोणतीही प्रमाणित रासायनिक फवारणी उपलब्ध नाही. कोणतेही अनधिकृत किंवा बंदी घातलेले कीटकनाशक (उदा. डायक्लोर्व्हॉस) फवारू नका.',
      hi: 'महत्वपूर्ण सूचना: लीफ वेबर कीट के लिए कोई रासायनिक छिड़काव सत्यापित नहीं है। कोई अनधिकृत या प्रतिबंधित कीटनाशक न छिड़कें।',
    },
    farmerAction: {
      en: [
        'Inspect shoot tips and webbed leaf clusters regularly.',
        'Manually collect and destroy folded / webbed leaves containing larvae in early infestation.',
        'Consult your local Krishi Vigyan Kendra (KVK) or agricultural extension officer for approved safe management.',
      ],
      mr: [
        'शेंड्याकडील पाने आणि जाळी बांधलेल्या पानांची नियमित पाहणी करा.',
        'सुरुवातीच्या काळात जाळी झालेली पाने अळीसह तोडून नष्ट करा.',
        'सध्याच्या अधिकृत व सुरक्षित कीड नियंत्रण उपायांसाठी स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी अधिकाऱ्यांचा सल्ला घ्या.',
      ],
      hi: [
        'शीर्ष पत्तियों और जाले वाले गुच्छों का नियमित निरीक्षण करें।',
        'शुरुआती अवस्था में जाले वाली पत्तियों को इल्ली सहित इकट्ठा कर नष्ट करें।',
        'वर्तमान में स्वीकृत सुरक्षित प्रबंधन उपायों के लिए स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।',
      ],
    },
  },
};

/**
 * Checks if a string contains non-trivial Devanagari script (Marathi/Hindi).
 */
export function hasDevanagari(text?: string | null): boolean {
  if (!text) return false;
  return /[\u0900-\u097F]/.test(text);
}

/**
 * Resolves standard disease key from raw name.
 */
export function normalizeDiseaseKey(rawName?: string | null): string | null {
  if (!rawName) return null;
  const lower = rawName.toLowerCase().trim();
  if (lower.includes('wilt')) return 'Wilt';
  if (lower.includes('leaf_spot') || lower.includes('leaf spot')) return 'Leaf_Spot';
  if (lower.includes('steril') || lower.includes('mosaic')) return 'Sterilic_mosaic';
  if (lower.includes('webber')) return 'Leaf_webber';
  if (lower.includes('healthy')) return 'Healthy';
  return null;
}

/**
 * Localizes recommendation data accurately for UI display and text-to-speech,
 * ensuring verified agricultural instructions are respected in the chosen language.
 */
export function getLocalizedRecommendation(
  data: ClaudeGuidanceResponse | null,
  language: Language,
  fallbackDisease?: string
): LocalizedRecommendation {
  const normKey = normalizeDiseaseKey(data?.disease_name || fallbackDisease);
  const entry = normKey ? VERIFIED_DISEASE_DATA[normKey] : null;

  const isHealthy = normKey === 'Healthy';
  const isWebber = normKey === 'Leaf_webber';

  const isSeedTreatment = !isHealthy && !isWebber && Boolean(
    normKey === 'Wilt' ||
    (data?.spray_guidance?.application_method &&
      (data.spray_guidance.application_method.toLowerCase().includes('seed treat') ||
       data.spray_guidance.application_method.toLowerCase().includes('soil application'))) ||
    Boolean(data?.important_alert && data.important_alert.toLowerCase().includes('seed treat'))
  );

  const isVerified = Boolean(
    data?.spray_guidance_available !== false &&
    entry &&
    normKey !== 'Leaf_webber' &&
    normKey !== 'Healthy'
  );

  // Fallbacks for header titles
  const headerTitle = isHealthy
    ? (language === 'mr' ? 'पीक आरोग्य सल्ला' : language === 'hi' ? 'फसल स्वास्थ्य सलाह' : 'CROP HEALTH ADVISORY')
    : isWebber
      ? (language === 'mr' ? 'कीड व्यवस्थापन सल्ला' : language === 'hi' ? 'कीट प्रबंधन सलाह' : 'PEST MANAGEMENT ADVISORY')
      : isSeedTreatment
        ? (language === 'mr' ? 'स्मार्ट उपचार मार्गदर्शन' : language === 'hi' ? 'स्मार्ट उपचार मार्गदर्शन' : 'SMART TREATMENT GUIDANCE')
        : (language === 'mr' ? 'स्मार्ट फवारणी मार्गदर्शन' : language === 'hi' ? 'स्मार्ट छिड़काव मार्गदर्शन' : 'SMART SPRAY GUIDANCE');

  const guidanceSectionTitle = isHealthy
    ? (language === 'mr' ? 'पीक निगा व व्यवस्थापन' : language === 'hi' ? 'फसल देखभाल और प्रबंधन' : 'Crop Care & Management')
    : isWebber
      ? (language === 'mr' ? 'सुरक्षित व्यवस्थापन मार्गदर्शन' : language === 'hi' ? 'सुरक्षित प्रबंधन मार्गदर्शन' : 'Safe Management Guidance')
      : isSeedTreatment
        ? (language === 'mr' ? 'बियाणे / जमीन उपचार मार्गदर्शन' : language === 'hi' ? 'बीज / मृदा उपचार मार्गदर्शन' : 'Seed / Soil Treatment Guidance')
        : (language === 'mr' ? 'फवारणी मार्गदर्शन' : language === 'hi' ? 'छिड़काव मार्गदर्शन' : 'Spray Guidance');

  const guidanceSectionSubtitle = isHealthy
    ? (language === 'mr' ? 'निरोगी पिकासाठी शिफारसी (फवारणीची गरज नाही)' : language === 'hi' ? 'स्वस्थ फसल हेतु अनुशंसाएं (छिड़काव की आवश्यकता नहीं)' : 'Care recommendations for healthy crop (No spraying needed)')
    : isWebber
      ? (language === 'mr' ? 'पाने गुंडाळणाऱ्या अळीसाठी सुरक्षित उपाय (रासायनिक फवारणी नाही)' : language === 'hi' ? 'लीफ वेबर के लिए सुरक्षित उपाय (रासायनिक छिड़काव नहीं)' : 'Safe measures for Leaf Webber (No chemical spray)')
      : isSeedTreatment
        ? (language === 'mr' ? 'पेरणीपूर्वी किंवा जमिनीत वापरताना काय करावे (पानांवर फवारणी करू नका)' : language === 'hi' ? 'बुवाई पूर्व या मिट्टी में उपयोग के समय क्या करें (पत्तियों पर छिड़काव न करें)' : 'Application before sowing or in soil (Do NOT spray on leaves)')
        : (language === 'mr' ? 'फवारणी करताना काय करावे' : language === 'hi' ? 'छिड़काव करते समय क्या करें' : 'What to do while spraying');

  const afterSectionTitle = isHealthy
    ? (language === 'mr' ? 'नियमित शेत काळजी' : language === 'hi' ? 'नियमित खेत देखभाल' : 'Regular Field Care')
    : isWebber
      ? (language === 'mr' ? 'नियमित निरीक्षण व काळजी' : language === 'hi' ? 'नियमित निरीक्षण एवं देखभाल' : 'Regular Monitoring & Care')
      : isSeedTreatment
        ? (language === 'mr' ? 'उपचारानंतरची खबरदारी' : language === 'hi' ? 'उपचार के बाद सावधानियां' : 'After Treatment Guidance')
        : (language === 'mr' ? 'फवारणीनंतर' : language === 'hi' ? 'छिड़काव के बाद' : 'After Spraying');

  const timingLabel = isHealthy
    ? (language === 'mr' ? 'तपासणीची वेळ' : language === 'hi' ? 'निरीक्षण का समय' : 'Monitoring Timing')
    : isWebber
      ? (language === 'mr' ? 'तपासणीची वेळ' : language === 'hi' ? 'निरीक्षण का समय' : 'Monitoring Timing')
      : isSeedTreatment
        ? (language === 'mr' ? 'वापराची वेळ' : language === 'hi' ? 'उपयोग का समय' : 'Application Timing')
        : (language === 'mr' ? 'फवारणीची वेळ' : language === 'hi' ? 'छिड़काव का समय' : 'Spray Timing');

  const methodLabel = isHealthy
    ? (language === 'mr' ? 'व्यवस्थापन पद्धत' : language === 'hi' ? 'प्रबंधन विधि' : 'Management Method')
    : isWebber
      ? (language === 'mr' ? 'व्यवस्थापन पद्धत' : language === 'hi' ? 'प्रबंधन विधि' : 'Management Method')
      : isSeedTreatment
        ? (language === 'mr' ? 'वापर पद्धत' : language === 'hi' ? 'उपयोग विधि' : 'Application Method')
        : (language === 'mr' ? 'फवारणी पद्धत' : language === 'hi' ? 'छिड़काव विधि' : 'Application Method');

  const confidenceDisclaimer = language === 'mr'
    ? 'मॉडेल खात्री ही पानातील लक्षणांचे साम्य दर्शवते; प्रत्यक्ष शेत तपासणी आवश्यक आहे.'
    : language === 'hi'
      ? 'मॉडल विश्वास पत्ती के लक्षणों की समानता दर्शाता है; खेत में प्रत्यक्ष सत्यापन आवश्यक है।'
      : 'Model confidence reflects visual pattern match; field verification is recommended.';

  // If backend returned Devanagari in the selected language, prioritize it; otherwise use verified localized entry
  const resolveField = (
    backendVal: string | null | undefined,
    entryDict: Record<Language, string> | undefined,
    fallback: string
  ): string => {
    if (backendVal && (language === 'en' || hasDevanagari(backendVal))) {
      return backendVal;
    }
    if (entryDict) {
      return entryDict[language] || entryDict.en || fallback;
    }
    return backendVal || fallback;
  };

  const treatment = resolveField(
    data?.spray_guidance?.treatment,
    entry?.treatment,
    isHealthy
      ? (language === 'mr' ? 'कोणत्याही रासायनिक फवारणीची आवश्यकता नाही' : language === 'hi' ? 'किसी रासायनिक छिड़काव की आवश्यकता नहीं है' : 'No chemical spray required')
      : isWebber
        ? (language === 'mr' ? 'कोणत्याही प्रमाणित रासायनिक फवारणीची शिफारस नाही' : language === 'hi' ? 'किसी सत्यापित रासायनिक छिड़काव की सिफारिश नहीं है' : 'No verified chemical spray recommended')
        : (language === 'mr' ? 'प्रमाणित उपचार माहिती उपलब्ध नाही' : language === 'hi' ? 'सत्यापित उपचार जानकारी उपलब्ध नहीं' : 'Verified treatment unavailable')
  );

  const activeIngredient = resolveField(
    data?.spray_guidance?.active_ingredient,
    entry?.activeIngredient,
    isHealthy
      ? (language === 'mr' ? 'लागू नाही (निरोगी पान)' : language === 'hi' ? 'लागू नहीं (स्वस्थ पत्ती)' : 'Not applicable (healthy leaf)')
      : isWebber
        ? (language === 'mr' ? 'लागू नाही (प्रमाणित रासायनिक शिफारस नाही)' : language === 'hi' ? 'लागू नहीं (सत्यापित रासायनिक सिफारिश नहीं)' : 'Not applicable (no verified chemical recommendation)')
        : (language === 'mr' ? 'सक्रिय घटक उपलब्ध नाही' : language === 'hi' ? 'सक्रिय घटक उपलब्ध नहीं' : 'Active ingredient unavailable')
  );

  const recommendedQuantity = resolveField(
    data?.spray_guidance?.recommended_quantity,
    entry?.recommendedQuantity,
    (isHealthy || isWebber)
      ? (language === 'mr' ? 'लागू नाही' : language === 'hi' ? 'लागू नहीं' : 'Not applicable')
      : (language === 'mr' ? 'लेबलनुसार' : language === 'hi' ? 'लेबल के अनुसार' : 'As per product label')
  );

  const waterQuantity = data?.spray_guidance?.water_quantity && (language === 'en' || hasDevanagari(data.spray_guidance.water_quantity))
    ? data.spray_guidance.water_quantity
    : entry?.waterQuantity[language] ?? data?.spray_guidance?.water_quantity ?? null;

  const perPumpQuantity = data?.spray_guidance?.per_pump_quantity && (language === 'en' || hasDevanagari(data.spray_guidance.per_pump_quantity))
    ? data.spray_guidance.per_pump_quantity
    : entry?.perPumpQuantity[language] ?? data?.spray_guidance?.per_pump_quantity ?? null;

  const applicationTiming = resolveField(
    data?.spray_guidance?.spray_timing,
    entry?.sprayTiming,
    isHealthy
      ? (language === 'mr' ? 'लागू नाही — आठवड्यातून दोनदा नियमित शेत पाहणी करा' : language === 'hi' ? 'लागू नहीं — सप्ताह में दो बार नियमित खेत निरीक्षण करें' : 'Not applicable — regular monitoring twice a week')
      : isWebber
        ? (language === 'mr' ? 'लागू नाही — शेंड्याकडील पानांचे नियमित निरीक्षण करा' : language === 'hi' ? 'लागू नहीं — शीर्ष पत्तियों का नियमित निरीक्षण करें' : 'Not applicable — regular monitoring of shoot tips')
        : (language === 'mr' ? 'उत्पादन लेबलवरील सूचनांचे पालन करा' : language === 'hi' ? 'उत्पाद लेबल के निर्देशों का पालन करें' : 'Follow product label instructions')
  );

  const applicationMethod = resolveField(
    data?.spray_guidance?.application_method,
    entry?.applicationMethod,
    isHealthy
      ? (language === 'mr' ? 'लागू नाही (फवारणी करू नका)' : language === 'hi' ? 'लागू नहीं (छिड़काव न करें)' : 'Not applicable (do not spray)')
      : isWebber
        ? (language === 'mr' ? 'भौतिक / एकात्मिक व्यवस्थापन (फवारणी करू नका)' : language === 'hi' ? 'भौतिक / एकीकृत प्रबंधन (छिड़काव न करें)' : 'Physical / Cultural management (do not spray)')
        : isSeedTreatment
          ? (language === 'mr' ? 'बियाणे / जमीन उपचार' : language === 'hi' ? 'बीज / मृदा उपचार' : 'Seed / Soil treatment')
          : (language === 'mr' ? 'पानांवर फवारणी' : language === 'hi' ? 'पत्तियों पर छिड़काव' : 'Foliar spray')
  );

  const diseaseExplanation = resolveField(
    data?.disease_explanation,
    entry?.diseaseExplanation,
    language === 'mr'
      ? 'ही परिस्थिती तूर पिकाच्या पानांवर परिणाम करते. प्रत्यक्ष शेत निरीक्षण करून योग्य व्यवस्थापन करा.'
      : language === 'hi'
        ? 'यह स्थिति तूर फसल की पत्तियों को प्रभावित करती है। खेत का प्रत्यक्ष निरीक्षण कर उचित प्रबंधन करें।'
        : 'This condition affects the leaves of your Tur plant. Inspect the crop regularly.'
  );

  const importantAlert = resolveField(
    data?.important_alert,
    entry?.importantAlert,
    isHealthy
      ? (language === 'mr'
          ? 'निरोगी पीक — कोणत्याही रासायनिक फवारणीची गरज नाही. अनावश्यक औषध फवारणी टाळा.'
          : language === 'hi'
            ? 'स्वस्थ फसल — किसी रासायनिक छिड़काव की आवश्यकता नहीं है। अनावश्यक दवा छिड़काव से बचें।'
            : 'HEALTHY CROP — NO chemical spray required. Avoid unnecessary pesticide applications.')
      : isSeedTreatment
        ? (language === 'mr'
            ? 'फक्त बियाणे / जमीन उपचार — पेरणीपूर्वी बियाण्यावर किंवा जमिनीत वापरावे, पानांवर फवारणी करू नका.'
            : language === 'hi'
              ? 'केवल बीज / मृदा उपचार — बुवाई से पहले बीजों पर या मिट्टी में उपयोग करें, पत्तियों पर छिड़काव न करें।'
              : 'SEED TREATMENT ONLY — Apply before sowing or to soil, not as a foliar spray.')
        : (language === 'mr'
            ? 'फवारणी करताना नेहमी पडताळलेली कृषी शिफारस आणि उत्पादन लेबलच्या सूचनांचे पालन करा.'
            : language === 'hi'
              ? 'छिड़काव करते समय हमेशा सत्यापित कृषि अनुशंसा और उत्पाद लेबल के निर्देशों का पालन करें।'
              : 'Follow the verified treatment recommendation and product-label instructions while spraying.')
  );

  const safetyPrecautions = (data?.spray_guidance?.safety_precautions && (language === 'en' || hasDevanagari(data.spray_guidance.safety_precautions)))
    ? [data.spray_guidance.safety_precautions]
    : entry?.safetyPrecautions[language] || [
        language === 'mr' ? 'फवारणी/उपचार करताना संरक्षक साधने वापरा.' : language === 'hi' ? 'सुरक्षात्मक कपड़े पहनें।' : 'Wear protective equipment.',
        language === 'mr' ? 'उत्पादन लेबलवरील सूचनांचे पालन करा.' : language === 'hi' ? 'उत्पाद लेबल के निर्देशों का पालन करें।' : 'Follow product label instructions.',
      ];

  const afterCareAdvisory = (data?.spray_guidance?.after_spray_advisory && (language === 'en' || hasDevanagari(data.spray_guidance.after_spray_advisory)))
    ? [data.spray_guidance.after_spray_advisory]
    : entry?.afterCareAdvisory[language] || (isSeedTreatment
      ? (language === 'mr'
          ? ['उपचारित बियाणे नेहमी सावलीत वाळवा, उन्हात ठेवू नका.', 'बियाणे हाताळल्यानंतर हात साबणाने स्वच्छ धुवा.', 'वाळवलेले बियाणे ओलावा आणि थेट सूर्यप्रकाशापासून दूर सुरक्षित ठेवा.']
          : language === 'hi'
            ? ['उपचारित बीजों को हमेशा छाया में सुखाएं, धूप में नहीं।', 'बीज संभालने के बाद हाथों को साबुन से अच्छी तरह धोएं।', 'उपचारित बीज को नमी और सीधी धूप से दूर रखें।']
            : ['Always shade-dry treated seeds; avoid direct sunlight exposure.', 'Wash hands thoroughly with soap after handling treated seeds.', 'Store treated seed safely away from moisture and direct sunlight.'])
      : (language === 'mr'
          ? ['फवारणी पंप योग्य प्रकारे स्वच्छ करा.', 'हात आणि उघडे भाग स्वच्छ धुवा.', 'पिकाचे नियमित निरीक्षण करा.']
          : language === 'hi'
            ? ['छिड़काव पंप को अच्छी तरह साफ करें।', 'हाथ और खुले अंगों को अच्छी तरह धोएं।', 'फसल की नियमित निगरानी करें।']
            : ['Clean the sprayer properly.', 'Wash hands and exposed areas.', 'Observe the crop regularly.']));

  const farmerAction = (data?.farmer_action?.length && (language === 'en' || hasDevanagari(data.farmer_action[0])))
    ? data.farmer_action
    : entry?.farmerAction[language] || [
        language === 'mr'
          ? 'तुमच्या तूर पिकाचे नियमित निरीक्षण करा. लक्षणे तशीच राहिल्यास किंवा वाढल्यास पुन्हा नवीन पान स्कॅन करा.'
          : language === 'hi'
            ? 'अपनी तूर फसल की नियमित निगरानी करें। यदि लक्षण बढ़ते हैं तो नई पत्ती स्कैन करें।'
            : 'Monitor your Tur crop regularly. If symptoms continue, scan a fresh leaf again.',
      ];

  return {
    isSeedTreatment,
    isHealthy,
    isWebber,
    isVerified,
    diseaseExplanation,
    treatment,
    activeIngredient,
    recommendedQuantity,
    waterQuantity,
    perPumpQuantity,
    applicationTiming,
    applicationMethod,
    safetyPrecautions,
    afterCareAdvisory,
    importantAlert,
    farmerAction,
    confidenceDisclaimer,
    headerTitle,
    guidanceSectionTitle,
    guidanceSectionSubtitle,
    afterSectionTitle,
    timingLabel,
    methodLabel,
  };
}
