# Acads AI Tutor - Your Free, Self‑Hosted Study Buddy

> *"I was using Gemini Pro and ChatGPT for a while-they were free, and they worked beautifully. But then the free trials started expiring, and the renewal notices hit my inbox. I thought, 'How am I going to study for my fluid mechanics exams without AI help?' So I built this. Now I have my own private AI tutor, running on my machine, using NVIDIA's latest models for free (yes, actually free), without worrying about monthly subscriptions."*

This is a **personal AI chat assistant** that you run on your own computer. It understands text, images, and even PDFs - perfect for going through lecture slides, past exam questions, or that one diagram you can't make sense of. It's designed for students who want a reliable study partner without paying a dime.

---

## What Makes This Special?

| Feature | What It Does |
| :------ | :----------- |
| **Multi‑Modal Q&A** | Ask about text, images, or PDFs - the AI sees everything you show it. |
| **PDF → Images Automatically** | Drop a PDF, and your browser converts every page to an image instantly (no server processing). |
| **Full Chat Memory** | The AI remembers your whole conversation, including images. Ask follow‑ups like *"go to the next slide"* without re‑uploading. |
| **Smart Fallback Chains** | If one free model is down or rate‑limited, the backend automatically tries another one. No more *"Model unavailable"* errors. |
| **Resizable Width** | Drag a slider to adjust the chat window width to your preference. |
| **Dark Mode** | Study late at night without eye strain. |
| **Drag, Drop & Paste** | Attach files by dragging them onto the page or pasting from the clipboard - super intuitive. |
| **Beautiful Math Rendering** | LaTeX equations render perfectly using KaTeX. No more ugly `x^2` approximations. |
| **Full Local Storage** | Your entire chat history (including images) is saved in your browser - close the tab, reopen it, and continue right where you left off. |

---

## How It Works (Under the Hood)

- **Frontend**: Plain HTML/CSS/JS - no frameworks, no build tools. Just open `index.html` and it works.
- **Backend**: FastAPI server that acts as a bridge between your browser and OpenRouter's AI models.
- **AI Models**: Uses OpenRouter's free tier. The backend has fallback chains so if NVIDIA's model is busy, it automatically switches to Llama or another model.
- **PDF Handling**: Everything happens in your browser - `pdf.js` converts PDFs to images, so your PDFs never leave your machine (privacy first!).

---

## Quick Start (The "5‑Minute Setup")

### 1. Get an OpenRouter API Key (It's Free!)

1. Go to [OpenRouter](https://openrouter.ai/keys) and sign up (email + password).
2. Once logged in, click **"Create Key"**.
3. Copy the key - it looks like `sk-or-v1-xxxxxxxxxxxxxxxxxx`.

### 2. Clone or Download This Repository

```bash
git clone <your-repo-url>
cd Acads-AI-Tutor
```

Or just download the ZIP and extract it somewhere.

### 3. Install the Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Your `.env` File

Create a file named `.env` in the same folder as `main.py`, and put your API key inside:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 5. Start the Backend Server

```bash
uvicorn main:app --reload
```

You'll see something like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

Keep this terminal window open - the server needs to stay running.

### 6. Open the Frontend

Double‑click `index.html` (or drag it into a browser tab). That's it - you're ready to chat!

---

## 📖 User Manual - Step by Step

### Asking a Question (Text Only)

1. Type your question in the text box at the bottom.
2. Press `Enter` (or click the **Ask** button).
3. The AI will reply in a chat bubble.

### Attaching an Image

**Option A - Click the 📎 button**:
- Click the paperclip icon next to the text box.
- Select one or more images (JPG, PNG, WEBP, etc.).

**Option B - Drag & Drop**:
- Drag an image from your desktop or file explorer directly onto the page.
- You'll see a *"Drop image or PDF"* overlay - release it.

**Option C - Paste from Clipboard**:
- Copy an image (e.g., take a screenshot with `Win+Shift+S` or `Cmd+Shift+4`).
- Press `Ctrl+V` (or `Cmd+V`) anywhere on the page.

### Attaching a PDF

- Drag a PDF onto the page, or use the 📎 button.
- The frontend will convert each page to an image (this may take a few seconds for large PDFs).
- All pages are sent as separate images - the AI will "see" the entire document.

### Asking About an Image or PDF

1. Attach your file(s) using any method above.
2. Type a question like *"Explain this diagram"* or *"What's the main point of this slide?"*
3. Press `Enter` - the AI will answer based on both your text and the attached images.

### Follow‑up Questions (The Magic Part)

After you've uploaded images, you can ask text‑only follow‑ups like:
- *"Go to the next slide."*
- *"Explain that equation again."*
- *"What's the physical meaning of this term?"*

The AI will still "see" the earlier images because the entire conversation (including images) is sent every time. No need to re‑upload!

### Adjusting the Chat Width

- Use the **"📐 Width"** slider at the top of the page.
- Drag left or right to make the chat window narrower or wider (30% - 100% of your screen).
- Your preference is saved automatically.

### Dark Mode

- Click the **🌙** button at the top right.
- It toggles to **☀️** - click again to go back to light mode.
- Your theme preference is saved automatically.

### Clearing the Chat

- Click **"Clear chat"**.
- Confirm the prompt - this will delete all messages and images from your browser's memory.
- **Warning**: This cannot be undone.

---

## How the Model Fallback Works

The backend uses multiple models so you're never stuck if one is down:

**Text‑only models** (when no images are present):
1. `nvidia/nemotron-3-ultra-550b-a55b:free` (primary)
2. `meta-llama/llama-3.3-70b-instruct:free` (backup)
3. `tencent/hy3:free` (second backup)

**Vision models** (when images/PDFs are attached):
1. `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` (primary)
2. `nvidia/nemotron-nano-12b-v2-vl:free` (backup)
3. `meta-llama/llama-3.2-11b-vision-instruct:free` (second backup)

If the first model fails (rate limit, "DEGRADED" function, timeout), the backend automatically retries with the next one. You won't even notice - the AI just keeps answering.

---

##  Troubleshooting

| Issue | Solution |
| :---- | :------- |
| **"Failed to fetch" error** | The backend server isn't running. Go back to your terminal and run `uvicorn main:app --reload`. |
| **"API key invalid"** | Check your `.env` file - make sure the key starts with `sk-or-v1-` and has no extra spaces. |
| **"No answer returned"** | OpenRouter's free tier might be rate‑limited. Wait 10‑15 seconds and try again - the fallback chain will switch models automatically. |
| **PDF doesn't convert** | Make sure your browser supports `pdf.js` - all modern browsers do. Try a smaller PDF first. |
| **Chat history disappears** | Did you clear your browser's cache? The history is stored in `localStorage` - if you clear it, the history is gone. |
| **Images don't render** | The data URL might be too large. Try compressing your image or using a smaller file. |

---

##  Why I Built This

Look, I'm a student. I love AI tools - they've saved my grades more times than I can count. But I can't afford ChatGPT Pro or Gemini Advanced. The free trials were great while they lasted, but once they expired, I was stuck.

So I started digging. OpenRouter gives you access to hundreds of models, and many of them have **free tiers**. NVIDIA's Nemotron models are surprisingly good - they're fast, they understand images, and they handle math and physics really well. The best part? They're completely free for personal use.

I thought, *"Why not build my own AI tutor?"* This is the result. It's not as polished as ChatGPT, but it's mine - I control it, it runs on my machine, and I don't have to worry about subscription renewals.

If you're a student like me, I hope this helps you get through your studies. It's not perfect, but it's honest, free, and built with love.

---

## Project Structure

```
Acads-AI-Tutor/
├── index.html          # The main frontend - open this in your browser
├── main.py             # The backend server (FastAPI)
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .env                # Your API key (create this yourself)
```

---

## Future Plans (If I Have Time)

- **Better error messages** - so you know exactly what went wrong.
- **Markdown export** - save the entire chat as a clean Markdown file for revision.
- **Voice input** - ask questions by speaking (if I figure out a free way to do it).
- **More models** - I'll keep updating the fallback chains as new free models appear.

---

## License

MIT - use it for anything, modify it, share it, sell it (if you can). Just don't forget to mention where you got it - I'd appreciate the credit.

---

##  Acknowledgements

- **OpenRouter** - for giving students free access to world‑class AI models.
- **NVIDIA** - for releasing such powerful models for free (you guys are heroes).
- **Llama/Meta** - for the open‑source models that keep the fallback chains alive.
- And to everyone who uses this - I hope it helps you pass your exams.

---

### Final Words

This is a passion project built by a student for students. It's not perfect, but it's honest. If you run into issues, please open an issue on GitHub - I'll try to help when I can.

Happy studying, and may your grades be high! 🎓

---

**P.S.** If you're wondering why the repo name is *"Acads AI Tutor"* - "Acads" is short for "Academics". I wanted something that felt personal, because that's exactly what this is - your personal AI tutor.
