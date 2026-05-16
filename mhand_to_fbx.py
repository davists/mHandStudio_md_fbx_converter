import argparse
import subprocess
import sys
import time
import shutil
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════
CFG = {
    "mhand_exe":       r"C:\Users\Locatech\Downloads\mHandStudio\mHandStudio\mHandStudio.exe",
    "output_dir":      "fbx",       # None = mesma pasta do .md
    "startup_timeout": 30,         # Aumentado de 20 para 30 segundos
    "ui_delay":        0.8,
    "window_title":    "mHandStudio",
    "force_restart":   True,       # Fechar e reiniciar para evitar cache de arquivos
    "fbx_format":      "binary",  # binary, ascii, 6.0-binary, 6.0-ascii
}


# ══════════════════════════════════════════════════════════════════════════════
# UI AUTOMATION (mHand Studio → FBX)
# ══════════════════════════════════════════════════════════════════════════════

def get_display_info():
    """
    Obtém informações de resolução e escala DPI do display.
    Retorna dict com screen_width, screen_height, dpi_scale.
    """
    import pyautogui
    try:
        import ctypes
        # Obter DPI awareness
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        pass
    
    # Resolução da tela
    screen_width, screen_height = pyautogui.size()
    
    # Detectar escala DPI (Windows)
    dpi_scale = 1.0
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        dpi = user32.GetDpiForSystem()
        dpi_scale = dpi / 96.0  # 96 DPI = 100% scale
    except Exception:
        # Fallback: tentar com win32api se disponível
        try:
            import win32api
            dc = win32api.GetDC(0)
            dpi_x = win32api.GetDeviceCaps(dc, 88)  # LOGPIXELSX
            win32api.ReleaseDC(0, dc)
            dpi_scale = dpi_x / 96.0
        except Exception:
            log.warning("Não foi possível detectar DPI, usando scale 1.0")
            dpi_scale = 1.0
    
    info = {
        "screen_width": screen_width,
        "screen_height": screen_height,
        "dpi_scale": dpi_scale
    }
    
    log.info("Display: %dx%d, DPI scale: %.2f", screen_width, screen_height, dpi_scale)
    return info


def check_deps():
    missing = []
    for pkg in ("pyautogui", "pygetwindow", "psutil"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        log.error("Dependências faltando: %s", ", ".join(missing))
        log.error("Instale com: pip install %s", " ".join(missing))
        sys.exit(1)


def close_mhand_studio():
    """
    Fecha todas as instâncias do mHand Studio em execução.
    Isso garante que o programa inicie limpo, sem cache de arquivos.
    """
    import psutil
    
    log.info("Procurando processos do mHand Studio para fechar...")
    closed = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'mHandStudio' in proc.info['name']:
                log.info("  Fechando processo: %s (PID: %d)", proc.info['name'], proc.info['pid'])
                proc.terminate()
                closed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if closed:
        log.info("Aguardando processos fecharem...")
        time.sleep(2)
        # Forçar fechamento se ainda estiver rodando
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'mHandStudio' in proc.info['name']:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(1)
    else:
        log.info("Nenhum processo do mHand Studio encontrado.")


def find_or_launch_mhand(force_restart=True):
    """
    Args:
        force_restart: Se True, fecha qualquer instância existente antes de iniciar
                      para garantir início limpo sem cache.
    """
    import pygetwindow as gw

    if force_restart:
        close_mhand_studio()
    else:
        log.info("Procurando mHand Studio...")
        wins = [w for w in gw.getAllWindows() if CFG["window_title"] in w.title]
        if wins:
            log.info("mHand Studio já está aberto.")
            try:
                wins[0].activate()
            except Exception:
                pass  # Ignorar erro de ativação
            time.sleep(CFG["ui_delay"])
            return wins[0]

    exe = CFG["mhand_exe"]
    if not Path(exe).exists():
        log.error("Executável não encontrado: %s", exe)
        sys.exit(1)

    log.info("Iniciando mHand Studio (sem cache)...")
    subprocess.Popen([exe])

    deadline = time.time() + CFG["startup_timeout"]
    while time.time() < deadline:
        time.sleep(1.5)
        wins = [w for w in gw.getAllWindows() if CFG["window_title"] in w.title]
        if wins:
            log.info("mHand Studio aberto.")
            try:
                wins[0].activate()
            except Exception:
                pass  # Ignorar erro de ativação
            # Aguardar mais tempo para o programa carregar completamente
            log.info("Aguardando mHandStudio carregar completamente...")
            time.sleep(5)  # Tempo extra para garantir que carregou
            return wins[0]

    log.error("Timeout: mHand Studio não abriu em %ds.", CFG["startup_timeout"])
    sys.exit(1)


def check_dropdown_opened(x: int, y: int) -> bool:
    """
    Verifica se dropdown abriu checando pixels próximos.
    Método simples sem OCR.
    
    Args:
        x, y: Coordenadas abaixo do dropdown onde a lista deveria aparecer
    
    Returns:
        True se detectou mudança indicando que abriu
    """
    try:
        import pyautogui as ag
        # Verificar pixel abaixo do dropdown (onde a lista aparece)
        test_y = y + 30  # 30px abaixo
        pixel = ag.pixel(x, test_y)
        
        # Lista de dropdown geralmente tem fundo branco/cinza claro
        # RGB aproximado: (240-255, 240-255, 240-255)
        r, g, b = pixel
        is_light = r > 230 and g > 230 and b > 230
        
        if is_light:
            log.info("    Detecção: dropdown provavelmente abriu (pixel claro detectado)")
            return True
        else:
            log.warning("    Detecção: dropdown pode não ter aberto (pixel escuro)")
            return False
    except Exception as e:
        log.warning("    Erro ao detectar pixel: %s", e)
        return False  # Assumir que não abriu em caso de erro


def handle_export_dialog(win, fbx_path: Path, display_info: dict):
    """
    Preenche o diálogo 数据导出 para exportar FBX.
    Usa coordenadas relativas adaptáveis a qualquer resolução.

    Layout do diálogo:
      ┌─────────────────────────────────┐
      │ 数据导出                        │
      │ 输出文件夹  [path field] [...]  │
      │ 文件名      [name field]        │
      │ 导出类型    [FBX ▾]             │
      │ 旋转顺序    [YXZ ▾]            │
      │            [  确定  ]           │
      └─────────────────────────────────┘
    """
    import pyautogui as ag

    wl, wt = win.left, win.top
    ww, wh = win.width, win.height

    dlg_cx = wl + ww // 2

    # Coordenadas proporcionais (testadas em 1456×816)
    y_folder   = wt + int(wh * 0.328)
    y_filename = wt + int(wh * 0.365)
    y_format   = wt + int(wh * 0.402)   # linha 导出类型
    y_ok       = wt + int(wh * 0.476)

    btn_folder_x = dlg_cx + int(ww * 0.117)
    
    # Screenshot inicial do diálogo para debug
    log.info("Diálogo de exportação aberto, capturando estado inicial...")
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_inicial.png"))
    time.sleep(0.5)

    # ── Pasta de saída ─────────────────────────────────────────────────────────
    # Pular configuração de pasta - mHandStudio exporta para MotionFiles por padrão
    # O script vai mover o arquivo depois
    log.info("  Pulando configuração de pasta (usar padrão MotionFiles)")
    
    # ── Nome do arquivo ────────────────────────────────────────────────────────
    log.info("  Definindo nome: %s", fbx_path.stem)
    ag.click(dlg_cx, y_filename)
    time.sleep(0.4)
    ag.hotkey("ctrl", "a")
    time.sleep(0.2)
    ag.typewrite(fbx_path.stem, interval=0.04)
    time.sleep(0.3)

    # ── Formato FBX ────────────────────────────────────────────────────────────
    log.info("  Selecionando formato FBX %s...", CFG["fbx_format"])
    
    # Abordagem mais robusta: clicar no campo + usar teclas
    # Primeiro, clicar no centro da linha do formato para dar foco
    log.info("  Clicando no campo de formato para dar foco...")
    ag.click(dlg_cx, y_format)
    time.sleep(0.5)
    
    # Screenshot antes de tentar abrir
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_antes_dropdown.png"))
    
    # Tentar abrir dropdown com ALT+DOWN (atalho padrão Windows)
    log.info("  Tentando abrir dropdown com Alt+Down...")
    ag.hotkey("alt", "down")
    time.sleep(0.8)
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_dropdown_altdown.png"))
    
    # Se não funcionou, tentar com F4 (outro atalho comum)
    log.info("  Tentando abrir dropdown com F4...")
    ag.press("f4")
    time.sleep(0.8)
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_dropdown_f4.png"))
    
    # Se ainda não funcionou, clicar na setinha
    log.info("  Tentando clicar na setinha do dropdown...")
    dropdown_arrow_x = dlg_cx + int(ww * 0.120)
    ag.click(dropdown_arrow_x, y_format)
    time.sleep(1.0)  # Aumentado de 0.8 para 1.0
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_dropdown_click.png"))
    
    # Garantir foco no dropdown clicando nele novamente
    log.info("  Garantindo foco no dropdown...")
    ag.click(dlg_cx, y_format)
    time.sleep(0.5)
    
    # Verificação opcional: checar se dropdown abriu (sem OCR)
    # Descomente para ativar verificação por pixel
    # if check_dropdown_opened(dlg_cx, y_format):
    #     log.info("✓ Dropdown confirmado como aberto")
    # else:
    #     log.warning("⚠ Dropdown pode não ter aberto, mas continuando...")
    
    # Navegar para FBX binary
    # Lista de opções (baseado na imagem):
    # 1. Biovision BVH(*.bvh) ← posição inicial
    # 2. Biovision BVH(*.bvh) 
    # 3. 3ds max biped(*.bvh)
    # 4. FBX binary(*.fbx) ← QUEREMOS ESTA ✅
    # 5. FBX ascii(*.fbx) ← NÃO esta ❌
    # 6. FBX encrypted(*.fbx)
    # 7. FBX 6.0 binary(*.fbx)
    # 8. FBX 6.0 ascii(*.fbx)
    
    log.info("  Navegando para FBX binary (posição 4 - NÃO ascii)...")
    log.info("  Aguardando dropdown estabilizar...")
    time.sleep(1.2)
    
    # Estratégia SIMPLES E CONFIÁVEL: HOME + exatamente 3 DOWNs
    # Não usar tecla 'F' pois pode pular para ascii
    
    log.info("  Voltando ao início da lista com HOME...")
    ag.press("home")
    time.sleep(0.5)
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_apos_home.png"))
    
    # Agora pressionar DOWN exatamente 3 vezes para chegar em FBX binary
    log.info("  Navegando: DOWN 3x para FBX binary (posição 4)...")
    
    for i in range(3):  # Exatamente 3 vezes para posição 4
        log.info("    DOWN %d/3 (pos %d -> pos %d)", i+1, i+1, i+2)
        ag.press("down")
        time.sleep(0.7)  # Tempo entre cada DOWN
        ag.screenshot(str(fbx_path.parent / f"_debug_dialog_down_{i+1}.png"))
    
    # CORREÇÃO: Se estava indo para posição 5 (ascii), voltar 1 posição
    log.info("  Correção: UP 1x para garantir posição 4 (FBX binary, NÃO ascii)...")
    ag.press("up")
    time.sleep(0.5)
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_correcao_up.png"))
    
    log.info("  Deve estar em FBX binary (posição 4) agora!")
    time.sleep(0.5)
    
    # Confirmar seleção
    log.info("  Confirmando seleção de FBX binary (deve estar na posição 4)...")
    time.sleep(0.3)
    
    # Screenshot imediatamente antes de confirmar
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_antes_enter.png"))
    
    # Confirmar com Enter
    ag.press("enter")
    time.sleep(CFG["ui_delay"])
    
    # Screenshot após confirmar
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_apos_enter.png"))
    
    # Aguardar um pouco e verificar se voltou ao estado normal do diálogo
    time.sleep(0.5)
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_formato_selecionado.png"))

    # ── Confirmar ──────────────────────────────────────────────────────────────
    log.info("  Aguardando antes de confirmar...")
    time.sleep(0.5)
    
    # Screenshot final antes de clicar OK
    ag.screenshot(str(fbx_path.parent / "_debug_dialog_antes_ok.png"))
    
    log.info("  Clicando 确定 para exportar FBX...")
    ag.click(dlg_cx, y_ok)
    time.sleep(CFG["ui_delay"] * 2)


def export_fbx_via_ui(md_path: Path, fbx_path: Path) -> bool:
    """
    Exporta arquivo .md diretamente para FBX via mHandStudio.
    Adapta-se automaticamente à resolução e DPI do monitor.
    
    Fluxo:
      1. Mudar para modo 编辑
      2. Deletar arquivo anterior
      3. Adicionar arquivo .md
      4. Carregar na timeline
      5. Exportar para FBX
    """
    import pyautogui as ag

    ag.FAILSAFE = True
    ag.PAUSE    = 0.1

    # Obter informações do display
    display_info = get_display_info()

    win = find_or_launch_mhand()
    
    wl, wt = win.left, win.top
    ww, wh = win.width, win.height
    log.info("Janela: (%d,%d) %dx%d", wl, wt, ww, wh)
    log.info("Display: %dx%d (DPI: %.2f%%)", 
             display_info["screen_width"], 
             display_info["screen_height"],
             display_info["dpi_scale"] * 100)
    
    # Posicionar cursor no centro da tela antes de começar
    # Isso evita erros de cliques quando o cursor está em posição aleatória
    log.info("Posicionando cursor no centro da tela...")
    center_x = wl + ww // 2
    center_y = wt + wh // 2
    ag.moveTo(center_x, center_y, duration=0.5)
    time.sleep(1)
    
    # Garantir que a janela está em foco - clicar no centro
    try:
        win.activate()
        time.sleep(1)
        ag.click(center_x, center_y)
        time.sleep(1)
    except Exception:
        pass
    
    # Salvar screenshot inicial para debug
    debug_dir = fbx_path.parent
    
    # Aguardar um pouco mais antes do primeiro screenshot para garantir que a interface carregou
    log.info("Aguardando interface carregar...")
    time.sleep(3)
    ag.screenshot(str(debug_dir / "_debug_0_inicial.png"))

    # Coordenadas dos menus no topo (proporcionais)
    menu_y = wt + int(wh * 0.033)
    
    # Menu 编辑 fica na 3ª posição (mHandPro, 交互, 编辑)
    # Posição horizontal proporcional à largura da janela
    btn_edit_menu_x = wl + int(ww * 0.145)

    # ── 0. Mudar para o modo 编辑 ─────────────────────────────────────────
    log.info("Passo 0: mudando para modo 编辑...")
    log.info("  Clicando em menu 编辑 em (%d, %d)", btn_edit_menu_x, menu_y)
    
    # Tentar clicar no menu algumas vezes se necessário
    for attempt in range(3):
        ag.click(btn_edit_menu_x, menu_y)
        time.sleep(CFG["ui_delay"] * 2)
        ag.screenshot(str(debug_dir / f"_debug_0b_modo_edit_tentativa_{attempt}.png"))
        # Assumir que funcionou e sair
        break

    # ── 2. Clicar no botão + ──────────────────────────────────────────────
    log.info("Passo 2: clicando no botão +...")
    plus_btn_x = wl + int(ww * 0.065)
    plus_btn_y = wt + wh - int(wh * 0.052)  # Proporcional à altura
    log.info("  Clicando em + em (%d, %d)", plus_btn_x, plus_btn_y)
    ag.click(plus_btn_x, plus_btn_y)
    time.sleep(CFG["ui_delay"] * 3)
    ag.screenshot(str(debug_dir / "_debug_2_dialog_aberto.png"))

    # ── 3. No diálogo do Windows, navegar até o arquivo ───────────────────
    log.info("Passo 3: navegando no diálogo do Windows...")
    ag.hotkey("alt", "d")  # Focar na barra de endereço
    time.sleep(0.5)
    ag.write(str(md_path.parent), interval=0.02)  # Digitar pasta
    time.sleep(0.3)
    ag.press("enter")
    time.sleep(CFG["ui_delay"] * 2)
    ag.screenshot(str(debug_dir / "_debug_3_pasta_navegada.png"))
    
    # Digitar nome do arquivo para selecioná-lo
    ag.write(md_path.name, interval=0.02)
    time.sleep(0.5)
    ag.press("enter")  # Confirmar seleção
    time.sleep(CFG["ui_delay"] * 2)
    ag.screenshot(str(debug_dir / "_debug_4_arquivo_selecionado.png"))

    # ── 4. Duplo clique no arquivo para carregá-lo na timeline ────────────
    log.info("Passo 4: duplo clique para carregar arquivo...")
    # Arquivo aparece na lista após ser adicionado (coordenadas proporcionais)
    file_list_x = wl + int(ww * 0.075)
    file_list_y = wt + int(wh * 0.480)
    log.info("  Duplo clique em (%d, %d)", file_list_x, file_list_y)
    # Fazer dois cliques separados em vez de doubleClick
    ag.click(file_list_x, file_list_y)
    time.sleep(0.1)
    ag.click(file_list_x, file_list_y)
    time.sleep(CFG["ui_delay"] * 5)  # Aguardar carregamento
    ag.screenshot(str(debug_dir / "_debug_5_arquivo_carregado.png"))

    # ── 5. Clicar no botão Export ──────────────────────────────────────────
    log.info("Passo 5: clicando no botão de exportação...")
    # Botão export fica no canto inferior direito, um pouco mais acima
    # Ajustado com base no feedback: botão estava um pouco mais acima
    export_positions = [
        (wl + ww - 25, wt + wh - 88),   # Posição 1: mais acima
    ]

    clicked = False
    for i, (export_btn_x, export_btn_y) in enumerate(export_positions):
        log.info("  Tentativa %d: clicando em (%d, %d)", i+1, export_btn_x, export_btn_y)
        ag.click(export_btn_x, export_btn_y)
        time.sleep(CFG["ui_delay"] * 2)
        ag.screenshot(str(debug_dir / f"_debug_6_{i}_tentativa_export.png"))
        
        # Dar tempo para verificar se o diálogo abriu
        time.sleep(1)
        clicked = True
        break  # Por enquanto, aceitar primeira tentativa

    if not clicked:
        log.error("Não foi possível clicar no botão de exportação")
        ag.screenshot(str(debug_dir / "_debug_6_falha_export.png"))
        close_mhand_studio()
        return False

    # ── 6. Preencher diálogo de exportação FBX ────────────────────────────
    log.info("Passo 6: preenchendo diálogo de exportação FBX...")
    time.sleep(CFG["ui_delay"])  # Aguardar diálogo abrir completamente
    handle_export_dialog(win, fbx_path, display_info)
    
    # Aguardar exportação finalizar (aumentar tempo)
    log.info("Aguardando exportação finalizar...")
    time.sleep(CFG["ui_delay"] * 5)  # Aumentado para 5x
    ag.screenshot(str(debug_dir / "_debug_7_apos_export.png"))

    # ── 7. Verificar se arquivo foi criado ─────────────────────────────────
    max_wait = 30  # Aumentado para 30 segundos
    elapsed = 0
    
    # mHandStudio exporta para a pasta MotionFiles por padrão
    motion_files_dir = Path(r"C:\Users\Locatech\automacao_mhand\MotionFiles")
    fbx_temp_path = motion_files_dir / fbx_path.name  # Arquivo temporário em MotionFiles
    
    log.info("Passo 7: verificando se FBX foi criado...")
    log.info("  Local de exportação (MotionFiles): %s", fbx_temp_path)
    log.info("  Destino final: %s", fbx_path)
    
    while elapsed < max_wait:
        # Verificar se foi criado em MotionFiles
        if fbx_temp_path.exists():
            file_size = fbx_temp_path.stat().st_size
            log.info("✓ FBX encontrado em MotionFiles: %s (%d bytes)", fbx_temp_path, file_size)
            
            # Mover para pasta de destino se for diferente
            if fbx_temp_path != fbx_path:
                log.info("  Movendo para destino final...")
                fbx_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(fbx_temp_path), str(fbx_path))
                log.info("✓ FBX movido com sucesso para: %s", fbx_path)
            
            ag.screenshot(str(debug_dir / "_debug_8_sucesso.png"))
            close_mhand_studio()
            return True
        
        # Também verificar no destino final (caso o diálogo tenha funcionado)
        if fbx_path.exists():
            file_size = fbx_path.stat().st_size
            log.info("✓ FBX exportado direto para destino: %s (%d bytes)", fbx_path, file_size)
            ag.screenshot(str(debug_dir / "_debug_8_sucesso.png"))
            close_mhand_studio()
            return True
        
        if elapsed % 5 == 0 and elapsed > 0:  # Log a cada 5 segundos
            log.info("  Aguardando... %ds de %ds", elapsed, max_wait)
        
        time.sleep(1)
        elapsed += 1
    
    log.error("✗ FBX não foi criado após %ds", max_wait)
    log.error("  Verificado em: %s", fbx_temp_path)
    log.error("  E também em: %s", fbx_path)
    log.error("  Verifique os screenshots em: %s", debug_dir)
    ag.screenshot(str(debug_dir / "_debug_8_falha.png"))
    close_mhand_studio()
    return False


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def process_file(md_path: Path) -> bool:
    out_dir  = Path(CFG["output_dir"]) if CFG["output_dir"] else md_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    fbx_path = out_dir / f"{md_path.stem}.fbx"

    log.info("═" * 60)
    log.info("Processando: %s", md_path.name)
    log.info("Saída: %s", fbx_path)

    return export_fbx_via_ui(md_path, fbx_path)


def main():
    parser = argparse.ArgumentParser(description="mHand .md → FBX (direto via mHandStudio)")
    parser.add_argument("--input",  "-i", required=True, help="Arquivo .md ou pasta para batch")
    parser.add_argument("--batch",        action="store_true", help="Processar todos .md na pasta")
    parser.add_argument("--output", "-o", help="Arquivo .fbx de saída (apenas modo single)")
    parser.add_argument("--output-dir",   help="Pasta de saída (modo batch)")
    parser.add_argument("--mhand-exe",    help="Caminho do mHandStudio.exe")
    parser.add_argument("--format",       choices=["binary", "ascii"], default="binary", help="Formato FBX")
    args = parser.parse_args()

    if args.output_dir:  CFG["output_dir"]  = args.output_dir
    if args.mhand_exe:   CFG["mhand_exe"]   = args.mhand_exe
    if args.format:      CFG["fbx_format"]  = args.format

    check_deps()
    input_path = Path(args.input)

    log.info("═══════════════════════════════════════════════════════")
    log.info("CONVERSÃO MD → FBX (DIRETO VIA mHandStudio)")
    log.info("═══════════════════════════════════════════════════════")

    if args.batch:
        files = sorted(input_path.glob("*.md"))
        if not files:
            log.warning("Nenhum .md em: %s", input_path)
            sys.exit(0)
        log.info("Modo batch: %d arquivo(s)", len(files))
        ok = sum(process_file(f) for f in files)
        log.info("═" * 60)
        log.info("Resultado: %d/%d com sucesso", ok, len(files))
        log.info("═" * 60)
    else:
        if not input_path.is_file():
            log.error("Arquivo não encontrado: %s", input_path)
            sys.exit(1)
        
        # Se --output foi especificado, atualizar CFG temporariamente
        if args.output:
            output_path = Path(args.output)
            CFG["output_dir"] = str(output_path.parent)
            # Renomear após exportação
            success = process_file(input_path)
            if success and output_path != input_path.with_suffix(".fbx"):
                import shutil
                default_fbx = input_path.parent / f"{input_path.stem}.fbx"
                if default_fbx.exists():
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(default_fbx), str(output_path))
                    log.info("Movido para: %s", output_path)
            sys.exit(0 if success else 1)
        else:
            sys.exit(0 if process_file(input_path) else 1)


if __name__ == "__main__":
    main()