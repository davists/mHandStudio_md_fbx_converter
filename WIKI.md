# 📚 Wiki - Automação mHandStudio para FBX

## 📋 Requisitos

### 🐍 Python
- **Versão:** Python 3.7 ou superior
- **Recomendado:** Python 3.9 - 3.11
- **Download:** https://www.python.org/downloads/

#### Instalação Python no Windows:
1. Baixe o instalador do Python
2. ✅ **IMPORTANTE:** Marque "Add Python to PATH" durante a instalação
3. Execute: `python --version` para verificar

---

## 📦 Dependências Python

### Bibliotecas Necessárias:

| Biblioteca | Versão | Descrição |
|------------|--------|-----------|
| `pyautogui` | >= 0.9.53 | Automação de interface (clicks, teclas, screenshots) |
| `pygetwindow` | >= 0.0.9 | Controle de janelas do Windows |
| `psutil` | >= 5.9.0 | Gerenciamento de processos |

### 🔧 Instalação das Dependências:

#### Método 1: Instalação Automática (Recomendado)
O script instala automaticamente as dependências na primeira execução:
```powershell
python mhand_to_fbx.py --input "caminho\arquivo.md"
```

#### Método 2: Instalação Manual
```powershell
pip install pyautogui pygetwindow psutil
```

#### Método 3: requirements.txt
Crie o arquivo `requirements.txt`:
```txt
pyautogui>=0.9.53
pygetwindow>=0.0.9
psutil>=5.9.0
```

Execute:
```powershell
pip install -r requirements.txt
```

---

## 🔍 Tesseract OCR (Opcional - Nova Funcionalidade!)

### ✨ **NOVO:** Versão OCR Disponível!

Agora você pode usar **OCR (Optical Character Recognition)** para automação mais inteligente e adaptável!

### 📊 Comparação: Legacy vs OCR

| Característica | Legacy (`mhand_to_fbx.py`) | OCR (`mhand_to_fbx_ocr.py`) |
|----------------|---------------------------|----------------------------|
| **Resolução** | Funciona apenas em resoluções específicas | ✅ Funciona em qualquer resolução |
| **DPI Scaling** | Quebra com escalas diferentes | ✅ Independente de DPI |
| **Mudanças UI** | Quebra se layout mudar | ✅ Auto-ajustável |
| **Multi-idioma** | Código separado por idioma | ✅ Detecta texto em inglês/chinês |
| **Debug** | Difícil diagnóstico | ✅ Screenshots de debug automáticos |
| **Setup** | Simples (só Python) | Requer Tesseract instalado |

### 🎯 Quando Usar OCR?

✅ **Use OCR se:**
- Trabalha com diferentes resoluções/monitores
- Precisa de automação mais confiável
- UI do mHandStudio muda frequentemente
- Quer suporte a menus em inglês

❌ **Use Legacy se:**
- Não quer instalar Tesseract
- Seu setup não muda nunca
- Prefere velocidade sobre robustez

### 📦 Instalação OCR (Opcional)

#### 1. Instalar Tesseract OCR no Windows:
```powershell
# Baixar instalador:
# https://github.com/UB-Mannheim/tesseract/wiki

# Arquivo: tesseract-ocr-w64-setup-5.3.x.exe
# Instalar com opção "Add to PATH" marcada ✅
```

**Caminho padrão:** `C:\Program Files\Tesseract-OCR\tesseract.exe`

#### 2. Instalar dependências Python para OCR:
```powershell
pip install -r requirements.txt
```

Isso instala:
- `opencv-python` - Processamento de imagens
- `pytesseract` - Wrapper Python para Tesseract
- `numpy` - Operações numéricas
- (dependências originais)

#### 3. Testar instalação OCR:
```powershell
# Verificar Tesseract
tesseract --version

# Rodar suite de testes
python test_ocr_setup.py
```

### 📖 Documentação Completa OCR:
Veja [OCR_SETUP.md](OCR_SETUP.md) para guia completo de instalação e uso.

---

## 🚀 Uso do Script

### 📝 Duas Versões Disponíveis:

1. **`mhand_to_fbx.py`** - Versão legacy (coordenadas fixas)
2. **`mhand_to_fbx_ocr.py`** - Versão OCR (inteligente e adaptável) ✨ **NOVO!**

### Sintaxe Básica (Legacy):
```powershell
python mhand_to_fbx.py --input "caminho\arquivo.md"
```

### Sintaxe Básica (OCR):
```powershell
python mhand_to_fbx_ocr.py --input "caminho\arquivo.md"
```

### Exemplos de Uso:

#### 1. Converter com OCR (Recomendado):
```powershell
python mhand_to_fbx_ocr.py --input "mao\Abastar.md"
```

#### 2. Converter sem OCR (Fallback):
```powershell
python mhand_to_fbx_ocr.py --input "mao\Abastar.md" --no-ocr
```

#### 3. Método Legacy (Original):
```powershell
python mhand_to_fbx.py --input "mao\Abastar.md"
```

#### 4. Batch processing com OCR:
Edite `md_to_fbx.ps1`:
```powershell
Get-ChildItem -Path "mao\*.md" -Recurse | ForEach-Object {
    Write-Host "Processing: $($_.Name)" -ForegroundColor Cyan
    python mhand_to_fbx_ocr.py --input $_.FullName
}
```

#### 3. Especificar pasta de saída:
```powershell
python mhand_to_fbx.py --input "mao\Abastar.md" --output-dir "exportados"
```

---

## 🎯 Configurações

### Configurações Principais (no código):

```python
CFG = {
    "mhand_exe":       r"C:\...\mHandStudio.exe",  # Caminho do executável
    "startup_timeout": 30,                          # Timeout para abrir (segundos)
    "ui_delay":        0.8,                         # Delay entre ações (segundos)
    "force_restart":   True,                        # Fechar instâncias anteriores
    "fbx_format":      "binary",                    # Formato: binary, ascii, etc
}
```

### Formatos FBX Disponíveis:
- `binary` - **FBX binary (Recomendado)** ✅
- `ascii` - FBX ascii (texto)
- `encrypted` - FBX encrypted
- `6.0-binary` - FBX 6.0 binary (compatibilidade)
- `6.0-ascii` - FBX 6.0 ascii (compatibilidade)

---

## 🐛 Troubleshooting

### ❌ Problema: "Python não é reconhecido como comando"
**Solução:**
1. Reinstale Python com "Add to PATH" marcado
2. OU adicione manualmente:
   - `C:\Users\<Usuario>\AppData\Local\Programs\Python\Python3X\`
   - `C:\Users\<Usuario>\AppData\Local\Programs\Python\Python3X\Scripts\`

### ❌ Problema: "ModuleNotFoundError: No module named 'pyautogui'"
**Solução:**
```powershell
pip install pyautogui pygetwindow psutil
```

### ❌ Problema: Script não encontra janela do mHandStudio
**Solução:**
1. Verifique o caminho do executável em `CFG["mhand_exe"]`
2. Execute mHandStudio manualmente primeiro
3. Aumente `CFG["startup_timeout"]` para 40-60 segundos

### ❌ Problema: Formato FBX errado sendo selecionado
**Solução:**
1. Verifique `CFG["fbx_format"] = "binary"`
2. Ajuste delays `CFG["ui_delay"]` para 1.0-1.5 segundos
3. Verifique screenshots de debug na pasta MotionFiles:
   - `_debug_dialog_apos_home.png`
   - `_debug_dialog_down_X.png`
   - `_debug_dialog_correcao_up.png`

### ❌ Problema: Coordenadas erradas em telas de DPI diferente
**Solução:**
O script detecta automaticamente DPI e resolução. Se houver problemas:
1. Verifique que não está usando zoom do Windows diferente de 100%
2. Execute: `python -c "import pyautogui; print(pyautogui.size())"`
3. Compare com sua resolução real

---

## 📊 Resolução e DPI

### Detecção Automática:
O script detecta automaticamente:
- ✅ Resolução da tela (ex: 1920x1080)
- ✅ DPI scaling do Windows (100%, 125%, 150%)
- ✅ Coordenadas proporcionais adaptativas

### Resoluções Testadas:
- ✅ 1920x1080 (Full HD)
- ✅ 2560x1440 (2K)
- ✅ 3840x2160 (4K)
- ✅ DPI 100%, 125%, 150%

---

## 📸 Debug Screenshots

Durante a execução, o script gera screenshots de debug em `MotionFiles\`:

| Screenshot | Descrição |
|------------|-----------|
| `_debug_window.png` | Janela inicial do mHandStudio |
| `_debug_add_button.png` | Botão + para adicionar arquivo |
| `_debug_file_dialog.png` | Diálogo de abrir arquivo |
| `_debug_file_loaded.png` | Arquivo carregado na timeline |
| `_debug_export_button.png` | Botão Export |
| `_debug_dialog_inicial.png` | Diálogo de exportação aberto |
| `_debug_dialog_apos_home.png` | Após pressionar HOME (posição 1) |
| `_debug_dialog_down_1.png` | Após 1º DOWN (posição 2) |
| `_debug_dialog_down_2.png` | Após 2º DOWN (posição 3) |
| `_debug_dialog_down_3.png` | Após 3º DOWN (posição 4) |
| `_debug_dialog_correcao_up.png` | Após UP de correção (FBX binary) |
| `_debug_dialog_antes_enter.png` | Antes de confirmar |
| `_debug_dialog_apos_enter.png` | Após confirmar |

---

## 📁 Estrutura de Arquivos

```
automacao_mhand/
├── mhand_to_fbx.py          # Script principal
├── WIKI.md                   # Esta documentação
├── requirements.txt          # (opcional) Lista de dependências
├── mao/                      # Pasta com arquivos .md de entrada
│   ├── Abastar.md
│   ├── Acordar.md
│   └── ...
└── MotionFiles/              # Pasta temporária (auto-criada)
    ├── *.fbx                 # Arquivos exportados temporariamente
    └── _debug_*.png          # Screenshots de debug
```

---

## 🔄 Fluxo de Execução

```
1. ✅ Instalar dependências (automático)
2. 🚀 Lançar mHandStudio.exe
3. 🪟 Localizar janela
4. ✏️ Entrar em modo Edit
5. ➕ Adicionar arquivo .md
6. 📋 Carregar na timeline (double-click)
7. 💾 Clicar em Export
8. 📝 Preencher nome do arquivo
9. 📂 Navegar dropdown (HOME + 3 DOWN + 1 UP)
10. ✅ Confirmar FBX binary
11. ⏳ Aguardar exportação
12. 🔍 Verificar arquivo .fbx criado
13. 📦 Mover para destino final
```

---

## 💡 Dicas

### Performance:
- Use `--batch` para processar múltiplos arquivos
- Reduza `ui_delay` para 0.5s se o PC for rápido
- Aumente para 1.2-1.5s se houver falhas intermitentes

### Debugging:
- Sempre verifique screenshots na pasta `MotionFiles\`
- Use modo verbose (adicione prints extras no código)
- Execute com uma janela do mHandStudio visível para acompanhar

### Produção:
- Minimize outras janelas durante automação
- Não mova o mouse manualmente durante execução
- Use resolução nativa (sem scaling diferente de 100% se possível)

---

## 📞 Suporte

### Logs:
O script gera logs detalhados no console com timestamps:
```
12:34:56  INFO      Iniciando conversão: Abastar.md → Abastar.fbx
12:34:57  INFO      ✓ mHandStudio encontrado (PID 12345)
12:35:00  INFO      Navegando: DOWN 1/3 (pos 1 -> pos 2)
```

### Verificação de Sistema:
```powershell
# Python
python --version

# Dependências
pip list | findstr "pyautogui pygetwindow psutil"

# Resolução
python -c "import pyautogui; print(pyautogui.size())"
```

---

## 📝 Changelog

### v1.0 (Atual)
- ✅ Detecção automática de resolução e DPI
- ✅ Navegação por teclado (HOME + DOWN + UP)
- ✅ Seleção correta de FBX binary (não ascii)
- ✅ Screenshots de debug detalhados
- ✅ Instalação automática de dependências
- ✅ Modo batch para múltiplos arquivos
- ✅ Suporte a paths relativos e absolutos

---

## 🎓 Glossário

| Termo | Significado |
|-------|-------------|
| **DPI** | Dots Per Inch - Scaling de interface do Windows (100%, 125%, etc) |
| **FBX** | Filmbox - Formato 3D da Autodesk para animações |
| **MD** | Formato proprietário de motion capture do mHandStudio |
| **UI Automation** | Automação de interface gráfica (clicks, teclas) |
| **OCR** | Optical Character Recognition - Reconhecimento de texto em imagens |
| **BVH** | Biovision Hierarchy - Formato de dados de captura de movimento |

---

**Última atualização:** 09/05/2026
**Versão:** 1.0
