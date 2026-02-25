# Deploy do backend no Render

Passo a passo para colocar a API de colorimetria no Render (plano gratuito).

---

## 1. Deixar o backend no GitHub

O Render faz deploy a partir de um repositório Git. Se o seu projeto **mdidas** já estiver no GitHub, pule para o passo 2.

Se ainda não estiver:

1. Crie um repositório no GitHub (ex.: `mdidas`).
2. Na pasta do projeto (onde estão `index.html`, `backend/`, etc.):

```powershell
cd c:\Users\Administrador\Documents\mdidas
git add .
git commit -m "Backend e app para deploy"
git remote add origin https://github.com/SEU_USUARIO/mdidas.git
git push -u origin main
```

(Substitua `SEU_USUARIO` pelo seu usuário do GitHub. Se já tiver `remote`, use só `git push`.)

---

## 2. Criar o Web Service no Render

1. Acesse **https://dashboard.render.com** e faça login.
2. Clique em **"New +"** → **"Web Service"**.
3. Conecte o **GitHub** (ou GitLab) se ainda não estiver conectado e autorize o Render a acessar seus repositórios.
4. Na lista, escolha o repositório **mdidas** (ou o nome que você deu).
5. Clique em **"Connect"**.

---

## 3. Configurar o serviço

Preencha assim:

| Campo | Valor |
|-------|--------|
| **Name** | `colorimetria` (ou outro nome; será parte da URL) |
| **Region** | Escolha a mais próxima (ex.: **Oregon (US West)** ou **Frankfurt**) |
| **Branch** | `main` (ou a branch que você usa) |
| **Root Directory** | `backend` ⚠️ **Importante:** só a pasta do backend. |
| **Runtime** | **Docker** |
| **Instance Type** | **Free** |

Deixe em branco (ou padrão):

- **Build Command** – o Render usa o Dockerfile.
- **Start Command** – já está no Dockerfile.

Não é obrigatório criar **Environment Variables**; o `PORT` o Render já define.

---

## 4. Deploy

1. Clique em **"Create Web Service"**.
2. O Render vai fazer o **build** (pode levar **5–15 minutos** na primeira vez: instala Python, OpenCV, MediaPipe, etc.).
3. Acompanhe o log. Se der erro, confira se **Root Directory** está exatamente **`backend`**.
4. Quando terminar, o status fica **"Live"** e aparece a URL do serviço, algo como:

   **https://colorimetria-xxxx.onrender.com**

Copie essa URL (sem barra no final).

---

## 5. Colocar a URL no app

1. Abra o arquivo **cores.html** na raiz do projeto (fora da pasta `backend`).
2. Procure:
   ```javascript
   var API_CORES_URL = "";
   ```
3. Troque para (use **sua** URL do Render):
   ```javascript
   var API_CORES_URL = "https://colorimetria-xxxx.onrender.com";
   ```
4. Salve e faça o deploy do site:
   ```powershell
   cd c:\Users\Administrador\Documents\mdidas
   firebase deploy
   ```

---

## 6. Testar

1. Abra **https://modi-5369d.web.app** (ou seu domínio).
2. Vá em **Minhas cores ideais**.
3. Envie as 3 fotos e clique em **Analisar minhas cores**.

**Importante no plano gratuito:** após ~15 min sem uso, o serviço **dorme**. A primeira requisição depois disso pode levar **30–60 segundos** (cold start). Vale esperar; se der timeout, tente de novo.

---

## Resumo rápido

| O quê | Onde |
|-------|------|
| Repo no GitHub | Projeto completo com pasta `backend/` |
| Render → New → Web Service | Repo **mdidas** |
| Root Directory | **backend** |
| Runtime | **Docker** |
| Instance Type | **Free** |
| URL no app | **cores.html** → `API_CORES_URL = "https://....onrender.com"` |
| Deploy do site | `firebase deploy` |

Se em algum passo aparecer erro (build ou ao analisar fotos), copie a mensagem ou um print do log do Render e dá para ajustar o próximo passo.
