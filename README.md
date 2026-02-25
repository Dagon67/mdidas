# Formato do Corpo – Costura

Site que exige **login com Google** para acessar e registra o **email do usuário como lead** no Firestore.

## O que foi implementado

- **Gate de acesso**: a pessoa só vê a ferramenta depois de entrar com Google.
- **Registro de lead**: ao fazer login, o email (e nome) é salvo na coleção `leads` do Firestore para você usar como lista de leads.

## Configuração (Firebase)

1. **Crie um projeto** em [Firebase Console](https://console.firebase.google.com/).

2. **Ative o Authentication**  
   - No menu: Build → Authentication → Get started  
   - Aba **Sign-in method** → **Google** → Enable → salve.

3. **Crie o Firestore**  
   - Build → Firestore Database → Create database  
   - Modo **Production** (ou Test para desenvolvimento).  
   - Escolha uma região (ex.: southamerica-east1).

4. **Regras do Firestore** (para a coleção `leads`)  
   Em Firestore → Rules, use algo assim para que só o próprio usuário registre o próprio email como lead:

   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /leads/{userId} {
         allow read, write: if request.auth != null && request.auth.uid == userId;
       }
     }
   }
   ```

5. **Config do projeto**  
   - Project settings (ícone de engrenagem) → Your apps → Web (</>).  
   - Registre o app e copie o objeto `firebaseConfig`.

6. **Colar no site**  
   No `index.html`, localize o objeto `firebaseConfig` e substitua pelos dados do seu projeto:

   ```javascript
   const firebaseConfig = {
     apiKey: "SUA_API_KEY",
     authDomain: "SEU_PROJETO.firebaseapp.com",
     projectId: "SEU_PROJETO_ID",
     storageBucket: "SEU_PROJETO.appspot.com",
     messagingSenderId: "SEU_SENDER_ID",
     appId: "SEU_APP_ID"
   };
   ```

## Onde ver os leads

No Firebase Console: **Firestore Database** → coleção **leads**.  
Cada documento tem:

- `email` – email do Google do usuário  
- `nome` – nome do perfil Google (se existir)  
- `criadoEm` – data/hora do primeiro acesso  

O ID do documento é o `uid` do usuário (cada pessoa fica com um registro por login).

## Desenvolvimento sem Firebase

Se você abrir o site **sem** configurar o `firebaseConfig` (deixando os placeholders), a tela de login é ignorada e o conteúdo é exibido direto, para você testar a ferramenta. No console do navegador aparece um aviso.
