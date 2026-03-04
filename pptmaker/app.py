import requests
import json
import base64
from flask import Flask, render_template, request

app = Flask(__name__)

DEEPSEEK_API_KEY = "sk-7baf760f0b664d8d8fb5db376eeee2e1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
PIXABAY_API_KEY = ""


def get_free_dict_data(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        resp = requests.get(url, timeout=5)
        return resp.json()[0] if resp.status_code == 200 else None
    except:
        return None


def get_audio_base64(en_data):
    phonetics = en_data.get('phonetics', [])
    audio_url = next((p['audio'] for p in phonetics if p.get('audio') and p['audio'].endswith('.mp3')), None)
    if not audio_url: return None
    if audio_url.startswith("//"): audio_url = "https:" + audio_url
    try:
        resp = requests.get(audio_url, timeout=5)
        return f"data:audio/mpeg;base64,{base64.b64encode(resp.content).decode('utf-8')}" if resp.status_code == 200 else None
    except:
        return None


def get_image_base64(query):
    search_url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&per_page=3"
    try:
        data = requests.get(search_url, timeout=5).json()
        if data['totalHits'] > 0:
            img_resp = requests.get(data['hits'][0]['webformatURL'], timeout=5)
            return f"data:image/jpeg;base64,{base64.b64encode(img_resp.content).decode('utf-8')}"
    except:
        return None


def get_deepseek_enhancement(word, en_data):
    has_phonetic = en_data.get('phonetic')
    input_context = []
    for i, m in enumerate(en_data.get('meanings', [])):
        defn = m['definitions'][0]['definition']
        ex = m['definitions'][0].get('example')
        input_context.append({
            "index": i,
            "pos": m['partOfSpeech'],
            "en_def": defn,
            "has_example": bool(ex),
            "en_ex": ex
        })

    prompt = f"""
    You are an academic lexicographer. For the word '{word}':
    1. Provide a concise Chinese translation for each English definition.
    2. For definitions where 'has_example' is true, translate the 'en_ex' into Chinese.
    3. FOR DEFINITIONS WHERE 'has_example' IS FALSE: Generate a high-quality, academic English example sentence and its Chinese translation.
    4. IF 'has_phonetic' IS FALSE: Provide the standard IPA phonetic transcription.
    5. Provide one authentic idiom using '{word}' and its Chinese meaning.

    Data Context: {json.dumps(input_context)}
    Has Phonetic in API: {bool(has_phonetic)}

    Return ONLY a JSON object:
    {{
      "ai_phonetic": "IPA_here_or_null",
      "meanings_enhanced": [
        {{ "zh_def": "...", "en_ex": "original_or_generated", "zh_ex": "..." }},
        ...
      ],
      "idiom": "...",
      "idiom_zh": "..."
    }}
    """

    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    try:
        resp = requests.post(f"{DEEPSEEK_BASE_URL}/chat/completions", headers=headers,
                             json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}],
                                   "response_format": {"type": "json_object"}})
        return json.loads(resp.json()['choices'][0]['message']['content'])
    except:
        return None


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        raw_words = request.form.get('words', '')
        word_list = [w.strip() for w in raw_words.replace('\n', ',').split(',') if w.strip()]
        final_results = []

        for word in word_list:
            en_data = get_free_dict_data(word)
            if not en_data: continue
            ai_data = get_deepseek_enhancement(word, en_data)
            display_phonetic = en_data.get('phonetic') or (ai_data.get('ai_phonetic') if ai_data else "N/A")
            meanings = []
            for i, m in enumerate(en_data.get('meanings', [])):
                enhanced = ai_data['meanings_enhanced'][i] if ai_data and i < len(ai_data['meanings_enhanced']) else {}

                meanings.append({
                    "pos": m['partOfSpeech'],
                    "en_def": m['definitions'][0]['definition'],
                    "zh_def": enhanced.get('zh_def', '翻译加载中...'),
                    "en_ex": m['definitions'][0].get('example') or enhanced.get('en_ex', ''),
                    "zh_ex": enhanced.get('zh_ex', '')
                })

            img_query = f"{word} {meanings[0]['zh_def'][:5]}"
            final_results.append({
                "word": word,
                "phonetic": display_phonetic,
                "audio": get_audio_base64(en_data),
                "image": get_image_base64(img_query),
                "meanings": meanings,
                "idiom": ai_data.get('idiom', 'N/A') if ai_data else 'N/A',
                "idiom_zh": ai_data.get('idiom_zh', '') if ai_data else ''
            })

        return render_template('result.html', results=final_results)
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
