import customtkinter as ctk
import yt_dlp as ytd
import threading
import os
import json
import time
import queue as q

from pathlib import Path
from tkinter import filedialog


# CONFIGURAÇÃO ---------------------------------------------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_NAME = "YouTube Downloader"
HISTORICO_MAXIMO = 20

PASTA_APP = Path.home() / ".youtube_downloader"
ARQUIVO_HISTORICO = PASTA_APP / "historico.json"

COR_AZUL = "#3B82F6"
COR_VERDE = "#22C55E"
COR_LARANJA = "#F59E0B"
COR_VERMELHA = "#EF4444"


# CLASSE PRINCIPAL -----------------------------------------------------------

class YouTubeDownloader(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("760x760")
        self.minsize(760, 760)
        self.resizable(False, False)

        # Ícone opcional
        try:
            self.iconbitmap("emblemdownloads_93482.ico")
        except Exception:
            pass

        # Variáveis do programa
        self.pasta = str(Path.home() / "Downloads")
        self.fila = q.Queue()

        self.baixando = False
        self.cancelamento = threading.Event()

        self.ultimo_arquivo = None
        self.historico = []

        self.dados_video = None
        self.consultando = False

        self.inicio_download = None
        self.tamanho_total = None

        self.protocol("WM_DELETE_WINDOW", self.fechar_aplicativo)

        self.carregar_historico()
        self.criar_interface()

        self.after(100, self.verificar_fila)

    # INTERFACE --------------------------------------------------------------

    def criar_interface(self):

        titulo = ctk.CTkLabel(
            self,
            text="YouTube Downloader",
            text_color="yellow",
            font=("Arial", 30, "bold")
        )
        titulo.pack(pady=(15, 3))

        subtitulo = ctk.CTkLabel(
            self,
            text="Baixe vídeos e áudios do YouTube",
            font=("Arial", 13)
        )
        subtitulo.pack(pady=(0, 12))

        # URL
        quadro_url = ctk.CTkFrame(self, fg_color="transparent")
        quadro_url.pack(fill="x", padx=35)

        self.url = ctk.CTkEntry(
            quadro_url,
            height=38,
            placeholder_text="Cole o link do vídeo aqui..."
        )
        self.url.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8)
        )

        self.botao_consultar = ctk.CTkButton(
            quadro_url,
            text="Consultar",
            width=100,
            height=38,
            command=self.consultar_video
        )
        self.botao_consultar.pack(side="right")

        # INFORMAÇÕES DO VÍDEO
        self.quadro_info = ctk.CTkFrame(self)
        self.quadro_info.pack(
            fill="x",
            padx=35,
            pady=(12, 5)
        )

        self.titulo_video = ctk.CTkLabel(
            self.quadro_info,
            text="Nenhum vídeo consultado",
            font=("Arial", 14, "bold"),
            anchor="w",
            justify="left",
            wraplength=650
        )
        self.titulo_video.pack(
            fill="x",
            padx=12,
            pady=(12, 6)
        )

        self.canal_video = ctk.CTkLabel(
            self.quadro_info,
            text="Canal: —",
            anchor="w"
        )
        self.canal_video.pack(
            fill="x",
            padx=12,
            pady=2
        )

        self.duracao_video = ctk.CTkLabel(
            self.quadro_info,
            text="Duração: —",
            anchor="w"
        )
        self.duracao_video.pack(
            fill="x",
            padx=12,
            pady=2
        )

        self.resolucao_video = ctk.CTkLabel(
            self.quadro_info,
            text="Resolução: —",
            anchor="w"
        )
        self.resolucao_video.pack(
            fill="x",
            padx=12,
            pady=(2, 12)
        )

        # FORMATO E QUALIDADE
        quadro_opcoes = ctk.CTkFrame(self, fg_color="transparent")
        quadro_opcoes.pack(
            fill="x",
            padx=35,
            pady=(8, 0)
        )

        self.formato = ctk.CTkOptionMenu(
            quadro_opcoes,
            values=["Vídeo MP4", "Áudio MP3"],
            command=self.atualizar_formato
        )
        self.formato.pack(
            side="left",
            expand=True,
            fill="x",
            padx=(0, 8)
        )

        self.qualidade = ctk.CTkOptionMenu(
            quadro_opcoes,
            values=[
                "Melhor disponível",
                "1080p",
                "720p",
                "360p"
            ]
        )
        self.qualidade.pack(
            side="left",
            expand=True,
            fill="x",
            padx=(8, 0)
        )

        # PASTA DE DESTINO
        self.botao_pasta = ctk.CTkButton(
            self,
            text="📂 Escolher pasta de destino",
            command=self.escolher_pasta
        )
        self.botao_pasta.pack(pady=(12, 4))

        self.texto_pasta = ctk.CTkLabel(
            self,
            text=self.pasta,
            wraplength=680
        )
        self.texto_pasta.pack(pady=2)

        # BOTÕES DE DOWNLOAD
        quadro_botoes = ctk.CTkFrame(self, fg_color="transparent")
        quadro_botoes.pack(pady=10)

        self.botao_baixar = ctk.CTkButton(
            quadro_botoes,
            text="⬇ BAIXAR",
            width=200,
            height=42,
            fg_color="#15803D",
            hover_color="#166534",
            font=("Arial", 16, "bold"),
            command=self.iniciar_download
        )
        self.botao_baixar.pack(side="left", padx=5)

        self.botao_cancelar = ctk.CTkButton(
            quadro_botoes,
            text="Cancelar",
            width=110,
            height=42,
            fg_color="#991B1B",
            hover_color="#7F1D1D",
            command=self.cancelar_download,
            state="disabled"
        )
        self.botao_cancelar.pack(side="left", padx=5)

        # STATUS
        self.resultado = ctk.CTkLabel(
            self,
            text="Aguardando download...",
            font=("Arial", 15, "bold"),
            wraplength=680
        )
        self.resultado.pack(pady=(5, 5))

        # BARRA DE PROGRESSO
        self.progresso = ctk.CTkProgressBar(
            self,
            width=680,
            height=16
        )
        self.progresso.pack(pady=5, padx=30)
        self.progresso.set(0)

        self.texto_progresso = ctk.CTkLabel(
            self,
            text="0%",
            font=("Arial", 13, "bold")
        )
        self.texto_progresso.pack(pady=2)

        self.velocidade = ctk.CTkLabel(
            self,
            text="Velocidade: —",
            font=("Arial", 12)
        )
        self.velocidade.pack(pady=2)

        self.tempo_restante = ctk.CTkLabel(
            self,
            text="Tempo restante: —",
            font=("Arial", 12)
        )
        self.tempo_restante.pack(pady=2)

        # ARQUIVO BAIXADO
        self.texto_arquivo = ctk.CTkLabel(
            self,
            text="",
            wraplength=680,
            justify="center"
        )
        self.texto_arquivo.pack(pady=(5, 2))

        self.botao_abrir_pasta = ctk.CTkButton(
            self,
            text="📂 Abrir pasta do arquivo",
            command=self.abrir_pasta,
            state="disabled"
        )
        self.botao_abrir_pasta.pack(pady=5)

        # HISTÓRICO
        self.titulo_historico = ctk.CTkLabel(
            self,
            text="Downloads recentes",
            font=("Arial", 16, "bold")
        )
        self.titulo_historico.pack(pady=(10, 3))

        self.lista_historico = ctk.CTkTextbox(
            self,
            width=680,
            height=105,
            font=("Consolas", 11)
        )
        self.lista_historico.pack(
            padx=30,
            pady=(0, 8)
        )
        self.lista_historico.configure(state="disabled")

        self.atualizar_historico_visual()

    # UTILITÁRIOS ------------------------------------------------------------

    @staticmethod
    def formatar_tempo(segundos):

        if segundos is None or segundos < 0:
            return "—"

        segundos = int(segundos)

        horas, resto = divmod(segundos, 3600)
        minutos, segundos = divmod(resto, 60)

        if horas:
            return f"{horas:02}:{minutos:02}:{segundos:02}"

        return f"{minutos:02}:{segundos:02}"

    @staticmethod
    def formatar_tamanho(bytes_total):

        if bytes_total is None:
            return "Desconhecido"

        tamanho = float(bytes_total)

        for unidade in ("B", "KB", "MB", "GB", "TB"):

            if tamanho < 1024 or unidade == "TB":
                return f"{tamanho:.2f} {unidade}"

            tamanho /= 1024

        return "Desconhecido"

    @staticmethod
    def formatar_duracao(segundos):

        if segundos is None:
            return "Desconhecida"

        return YouTubeDownloader.formatar_tempo(segundos)

    @staticmethod
    def extrair_mensagem_erro(erro):

        mensagem = str(erro)
        texto = mensagem.lower()

        if any(palavra in texto for palavra in (
            "private video",
            "video is private",
            "video unavailable",
            "has been removed",
            "not available"
        )):
            return "O vídeo está indisponível ou é privado."

        if any(palavra in texto for palavra in (
            "unsupported url",
            "invalid url",
            "url"
        )):
            return "Não foi possível reconhecer o endereço do vídeo."

        if any(palavra in texto for palavra in (
            "ffmpeg",
            "ffprobe"
        )):
            return (
                "Falha no processamento do arquivo. "
                "Verifique se o FFmpeg está instalado."
            )

        if any(palavra in texto for palavra in (
            "timed out",
            "connection",
            "network",
            "temporary failure"
        )):
            return (
                "Problema de conexão. "
                "Verifique sua internet e tente novamente."
            )

        return (
            "Não foi possível concluir a operação. "
            "Consulte os detalhes técnicos no terminal."
        )

    def enviar(self, *mensagem):
        """Envia mensagens da thread de trabalho para a interface."""
        self.fila.put(mensagem)

    # FORMATO ----------------------------------------------------------------

    def atualizar_formato(self, formato):

        if formato == "Áudio MP3":

            self.qualidade.configure(
                values=["Melhor disponível"]
            )
            self.qualidade.set("Melhor disponível")

        else:

            self.qualidade.configure(
                values=[
                    "Melhor disponível",
                    "1080p",
                    "720p",
                    "360p"
                ]
            )
            self.qualidade.set("Melhor disponível")

    # ESCOLHER PASTA ---------------------------------------------------------

    def escolher_pasta(self):

        pasta = filedialog.askdirectory(
            title="Selecione a pasta de destino",
            initialdir=self.pasta
        )

        if pasta:

            self.pasta = pasta
            self.texto_pasta.configure(text=self.pasta)

    # CONSULTAR VÍDEO --------------------------------------------------------

    def consultar_video(self):

        if self.baixando or self.consultando:
            return

        url = self.url.get().strip()

        if not url.startswith(("https://", "http://")):

            self.resultado.configure(
                text="Cole um endereço HTTP ou HTTPS válido.",
                text_color=COR_LARANJA
            )
            return

        self.consultando = True

        self.botao_consultar.configure(
            state="disabled",
            text="Consultando..."
        )

        self.resultado.configure(
            text="Consultando informações do vídeo...",
            text_color=COR_AZUL
        )

        self.progresso.configure(mode="indeterminate")
        self.progresso.start()

        threading.Thread(
            target=self.consultar_em_segundo_plano,
            args=(url,),
            daemon=True
        ).start()

    def consultar_em_segundo_plano(self, url):

        try:

            opcoes = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True
            }

            with ytd.YoutubeDL(opcoes) as ydl:
                info = ydl.extract_info(url, download=False)

            self.enviar("consulta_ok", info)

        except Exception as erro:

            print(f"Erro na consulta: {erro}")

            self.enviar(
                "consulta_erro",
                self.extrair_mensagem_erro(erro),
                str(erro)
            )

    def exibir_video(self, info):

        self.dados_video = info

        titulo = info.get("title") or "Título desconhecido"
        canal = (
            info.get("channel")
            or info.get("uploader")
            or "Desconhecido"
        )
        duracao = info.get("duration")

        resolucoes = [
            formato.get("height")
            for formato in info.get("formats", [])
            if formato.get("height")
        ]

        resolucao = (
            f"até {max(resolucoes)}p"
            if resolucoes
            else "Não identificada"
        )

        self.titulo_video.configure(text=titulo)
        self.canal_video.configure(text=f"Canal: {canal}")

        self.duracao_video.configure(
            text=f"Duração: {self.formatar_duracao(duracao)}"
        )

        self.resolucao_video.configure(
            text=f"Resolução: {resolucao}"
        )

    # NOMES DE ARQUIVO -------------------------------------------------------

    def gerar_nome_disponivel(self, pasta, titulo):

        nome = ytd.utils.sanitize_filename(
            titulo,
            restricted=False
        )

        for caractere in '<>:"/\\|?*':
            nome = nome.replace(caractere, "_")

        nome = nome.strip().rstrip(". ")

        if not nome:
            nome = "video"

        nome = nome[:150].rstrip(". ")

        contador = 0

        while True:

            nome_teste = (
                nome if contador == 0
                else f"{nome} ({contador})"
            )

            if not any(Path(pasta).glob(f"{nome_teste}.*")):
                return nome_teste

            contador += 1

    # INICIAR DOWNLOAD -------------------------------------------------------

    def iniciar_download(self):

        if self.baixando or self.consultando:
            return

        url = self.url.get().strip()

        if not url:

            self.resultado.configure(
                text="Cole o link de um vídeo primeiro.",
                text_color=COR_LARANJA
            )
            return

        if not url.startswith(("https://", "http://")):

            self.resultado.configure(
                text="O endereço informado não é válido.",
                text_color=COR_LARANJA
            )
            return

        formato = self.formato.get()
        qualidade = self.qualidade.get()
        pasta = self.pasta

        self.baixando = True
        self.cancelamento.clear()

        self.inicio_download = time.time()
        self.tamanho_total = None
        self.ultimo_arquivo = None

        self.botao_baixar.configure(
            state="disabled",
            text="BAIXANDO..."
        )

        self.botao_cancelar.configure(state="normal")
        self.botao_consultar.configure(state="disabled")
        self.botao_abrir_pasta.configure(state="disabled")

        self.progresso.stop()
        self.progresso.configure(mode="determinate")
        self.progresso.set(0)

        self.texto_progresso.configure(text="0%")
        self.velocidade.configure(text="Velocidade: —")
        self.tempo_restante.configure(text="Tempo restante: —")
        self.texto_arquivo.configure(text="")

        self.resultado.configure(
            text="Preparando download...",
            text_color=COR_AZUL
        )

        threading.Thread(
            target=self.baixar,
            args=(url, formato, qualidade, pasta),
            daemon=True
        ).start()

    # CANCELAR DOWNLOAD -----------------------------------------------------

    def cancelar_download(self):

        if not self.baixando:
            return

        self.cancelamento.set()

        self.botao_cancelar.configure(
            state="disabled",
            text="Cancelando..."
        )

        self.resultado.configure(
            text="Solicitando cancelamento...",
            text_color=COR_LARANJA
        )

    # DOWNLOAD ---------------------------------------------------------------

    def baixar(self, url, formato, qualidade, pasta):

        caminho_final = None

        try:

            destino = Path(pasta)
            destino.mkdir(parents=True, exist_ok=True)

            if self.cancelamento.is_set():
                raise InterruptedError("Download cancelado.")

            self.enviar(
                "status",
                "Consultando informações do vídeo..."
            )

            opcoes_info = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True
            }

            with ytd.YoutubeDL(opcoes_info) as ydl:
                info = ydl.extract_info(url, download=False)

            if self.cancelamento.is_set():
                raise InterruptedError("Download cancelado.")

            titulo = info.get("title") or "video"

            self.enviar("video_download", info)

            nome_final = self.gerar_nome_disponivel(
                destino,
                titulo
            )

            modelo = str(destino / f"{nome_final}.%(ext)s")

            opcoes = {
                "outtmpl": modelo,
                "noplaylist": True,
                "windowsfilenames": True,
                "overwrites": False,
                "progress_hooks": [self.atualizar_progresso],
                "continuedl": True,
                "nopart": False
            }

            if formato == "Vídeo MP4":

                opcoes["merge_output_format"] = "mp4"

                if qualidade == "Melhor disponível":

                    opcoes["format"] = (
                        "bestvideo+bestaudio/best"
                    )

                else:

                    altura = qualidade.replace("p", "")

                    opcoes["format"] = (
                        f"bestvideo[height<={altura}]"
                        f"+bestaudio/"
                        f"best[height<={altura}]"
                    )

            else:

                opcoes["format"] = "bestaudio/best"

                opcoes["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192"
                    }
                ]

            opcoes["progress_hooks"].append(
                self.verificar_cancelamento
            )

            self.enviar(
                "status",
                "Iniciando download..."
            )

            with ytd.YoutubeDL(opcoes) as ydl:
                resultado = ydl.extract_info(url, download=True)

            caminho_informado = (
                resultado.get("filepath")
                or resultado.get("_filename")
            )

            if caminho_informado:

                arquivo = Path(caminho_informado)

                if arquivo.is_file():

                    caminho_final = str(arquivo.resolve())

                else:

                    candidatos = [
                        item
                        for item in destino.glob(f"{nome_final}.*")
                        if item.is_file()
                        and not item.name.endswith((".part", ".ytdl"))
                    ]

                    if candidatos:

                        escolhido = max(
                            candidatos,
                            key=lambda item: item.stat().st_mtime
                        )

                        caminho_final = str(escolhido.resolve())

            if not caminho_final:

                candidatos = [
                    item
                    for item in destino.glob(f"{nome_final}.*")
                    if item.is_file()
                    and not item.name.endswith((".part", ".ytdl"))
                    and item.suffix.lower() in {
                        ".mp4", ".mp3", ".webm", ".mkv",
                        ".m4a", ".mov", ".avi", ".opus",
                        ".flv", ".ogg"
                    }
                ]

                if candidatos:

                    escolhido = max(
                        candidatos,
                        key=lambda item: item.stat().st_mtime
                    )

                    caminho_final = str(escolhido.resolve())

            if self.cancelamento.is_set():
                raise InterruptedError("Download cancelado.")

            self.enviar(
                "fim",
                True,
                "Download concluído com sucesso!",
                caminho_final,
                titulo,
                formato,
                qualidade
            )

        except Exception as erro:

            cancelado = (
                self.cancelamento.is_set()
                or isinstance(erro, InterruptedError)
            )

            if cancelado:

                self.enviar(
                    "cancelado",
                    "Download cancelado."
                )

            else:

                mensagem = self.extrair_mensagem_erro(erro)

                print(f"\nERRO NO DOWNLOAD: {erro}")

                self.enviar(
                    "fim",
                    False,
                    mensagem,
                    None,
                    str(erro),
                    formato,
                    qualidade
                )

    def verificar_cancelamento(self, dados):

        if self.cancelamento.is_set():
            raise ytd.utils.DownloadError(
                "Download cancelado pelo usuário."
            )

    # ATUALIZAR PROGRESSO ----------------------------------------------------

    def atualizar_progresso(self, dados):

        estado = dados.get("status")

        if estado == "downloading":

            baixado = dados.get("downloaded_bytes", 0)

            total = (
                dados.get("total_bytes")
                or dados.get("total_bytes_estimate")
            )

            porcentagem = (
                baixado / total
                if total
                else 0
            )

            velocidade = dados.get("speed")
            restante = dados.get("eta")

            self.enviar(
                "progresso",
                porcentagem,
                baixado,
                total,
                velocidade,
                restante
            )

        elif estado == "finished":

            self.enviar(
                "status",
                "Processando e finalizando arquivo..."
            )

    # FILA DE MENSAGENS ------------------------------------------------------

    def verificar_fila(self):

        try:

            while True:

                mensagem = self.fila.get_nowait()
                tipo = mensagem[0]

                if tipo == "status":

                    self.resultado.configure(
                        text=mensagem[1],
                        text_color=COR_AZUL
                    )

                elif tipo == "progresso":

                    (
                        _,
                        porcentagem,
                        baixado,
                        total,
                        velocidade,
                        restante
                    ) = mensagem

                    porcentagem = max(
                        0,
                        min(1, porcentagem)
                    )

                    self.progresso.set(porcentagem)

                    if total:

                        texto = (
                            f"{porcentagem * 100:.1f}%  |  "
                            f"{self.formatar_tamanho(baixado)} / "
                            f"{self.formatar_tamanho(total)}"
                        )

                    else:

                        texto = (
                            f"{porcentagem * 100:.1f}%  |  "
                            f"{self.formatar_tamanho(baixado)} baixados"
                        )

                    self.texto_progresso.configure(text=texto)

                    self.velocidade.configure(
                        text=(
                            f"Velocidade: "
                            f"{self.formatar_tamanho(velocidade)}/s"
                            if velocidade
                            else "Velocidade: calculando..."
                        )
                    )

                    self.tempo_restante.configure(
                        text=(
                            f"Tempo restante: "
                            f"{self.formatar_tempo(restante)}"
                            if restante is not None
                            else "Tempo restante: calculando..."
                        )
                    )

                    self.resultado.configure(
                        text="Baixando vídeo...",
                        text_color=COR_AZUL
                    )

                elif tipo == "video_download":

                    self.exibir_video(mensagem[1])

                elif tipo == "consulta_ok":

                    self.consultando = False

                    self.progresso.stop()
                    self.progresso.configure(mode="determinate")
                    self.progresso.set(0)

                    self.botao_consultar.configure(
                        state="normal",
                        text="Consultar"
                    )

                    self.exibir_video(mensagem[1])

                    self.resultado.configure(
                        text="Vídeo identificado. Pronto para baixar.",
                        text_color=COR_VERDE
                    )

                elif tipo == "consulta_erro":

                    self.consultando = False

                    self.progresso.stop()
                    self.progresso.configure(mode="determinate")
                    self.progresso.set(0)

                    self.botao_consultar.configure(
                        state="normal",
                        text="Consultar"
                    )

                    self.resultado.configure(
                        text=mensagem[1],
                        text_color=COR_LARANJA
                    )

                    print(f"Detalhes da consulta: {mensagem[2]}")

                elif tipo == "fim":

                    (
                        _,
                        sucesso,
                        texto,
                        caminho,
                        titulo,
                        formato,
                        qualidade
                    ) = mensagem

                    self.baixando = False

                    self.botao_baixar.configure(
                        state="normal",
                        text="⬇ BAIXAR"
                    )

                    self.botao_cancelar.configure(
                        state="disabled",
                        text="Cancelar"
                    )

                    self.botao_consultar.configure(
                        state="normal",
                        text="Consultar"
                    )

                    if sucesso:

                        self.progresso.set(1)

                        self.texto_progresso.configure(
                            text="100% — Concluído"
                        )

                        self.resultado.configure(
                            text=texto,
                            text_color=COR_VERDE
                        )

                        self.ultimo_arquivo = caminho

                        if caminho and Path(caminho).is_file():

                            arquivo = Path(caminho)

                            self.texto_arquivo.configure(
                                text=(
                                    f"Arquivo baixado: {arquivo.name}\n"
                                    f"Local: {arquivo.parent}"
                                )
                            )

                            self.botao_abrir_pasta.configure(
                                state="normal"
                            )

                        else:

                            self.texto_arquivo.configure(
                                text=(
                                    "Download concluído, mas não foi "
                                    "possível identificar o arquivo final."
                                )
                            )

                        self.velocidade.configure(
                            text="Velocidade: —"
                        )

                        self.tempo_restante.configure(
                            text="Tempo restante: 00:00"
                        )

                        self.url.delete(0, "end")

                        self.registrar_historico(
                            titulo,
                            caminho,
                            formato,
                            qualidade,
                            "Concluído"
                        )

                        self.notificar(
                            "Download concluído",
                            titulo
                        )

                    else:

                        self.resultado.configure(
                            text=texto,
                            text_color=COR_VERMELHA
                        )

                        self.velocidade.configure(
                            text="Download não concluído."
                        )

                        self.tempo_restante.configure(text="")

                        print(f"Detalhes técnicos: {mensagem[4]}")

                        self.registrar_historico(
                            titulo,
                            None,
                            formato,
                            qualidade,
                            "Falhou"
                        )

                elif tipo == "cancelado":

                    self.baixando = False

                    self.botao_baixar.configure(
                        state="normal",
                        text="⬇ BAIXAR"
                    )

                    self.botao_cancelar.configure(
                        state="disabled",
                        text="Cancelar"
                    )

                    self.botao_consultar.configure(
                        state="normal"
                    )

                    self.resultado.configure(
                        text=mensagem[1],
                        text_color=COR_LARANJA
                    )

                    self.velocidade.configure(
                        text="Download interrompido."
                    )

                    self.tempo_restante.configure(text="")

        except q.Empty:
            pass

        if self.winfo_exists():
            self.after(100, self.verificar_fila)

    # ABRIR PASTA ------------------------------------------------------------

    def abrir_pasta(self):

        if not self.ultimo_arquivo:
            return

        caminho = Path(self.ultimo_arquivo)

        pasta = caminho.parent if caminho.is_file() else caminho

        if not pasta.exists():

            self.resultado.configure(
                text="A pasta ou arquivo não foi encontrado.",
                text_color=COR_LARANJA
            )
            return

        try:
            os.startfile(str(pasta))

        except Exception as erro:

            self.resultado.configure(
                text=f"Não foi possível abrir a pasta: {erro}",
                text_color=COR_LARANJA
            )

    # HISTÓRICO --------------------------------------------------------------

    def carregar_historico(self):

        try:

            if ARQUIVO_HISTORICO.exists():

                with open(
                    ARQUIVO_HISTORICO,
                    "r",
                    encoding="utf-8"
                ) as arquivo:

                    dados = json.load(arquivo)

                    if isinstance(dados, list):
                        self.historico = dados[:HISTORICO_MAXIMO]

        except (OSError, json.JSONDecodeError) as erro:

            print(f"Não foi possível carregar o histórico: {erro}")
            self.historico = []

    def salvar_historico(self):

        try:

            PASTA_APP.mkdir(
                parents=True,
                exist_ok=True
            )

            temporario = ARQUIVO_HISTORICO.with_suffix(".tmp")

            with open(
                temporario,
                "w",
                encoding="utf-8"
            ) as arquivo:

                json.dump(
                    self.historico,
                    arquivo,
                    ensure_ascii=False,
                    indent=2
                )

            temporario.replace(ARQUIVO_HISTORICO)

        except OSError as erro:

            print(f"Não foi possível salvar o histórico: {erro}")

    def registrar_historico(
        self,
        titulo,
        caminho,
        formato,
        qualidade,
        status
    ):

        registro = {
            "titulo": titulo,
            "caminho": caminho,
            "formato": formato,
            "qualidade": qualidade,
            "status": status,
            "data": time.strftime("%d/%m/%Y %H:%M")
        }

        self.historico.insert(0, registro)

        self.historico = self.historico[:HISTORICO_MAXIMO]

        self.salvar_historico()
        self.atualizar_historico_visual()

    def atualizar_historico_visual(self):

        if not hasattr(self, "lista_historico"):
            return

        self.lista_historico.configure(state="normal")
        self.lista_historico.delete("1.0", "end")

        if not self.historico:

            self.lista_historico.insert(
                "end",
                "Nenhum download registrado ainda."
            )

        else:

            for item in self.historico:

                simbolo = (
                    "✓"
                    if item.get("status") == "Concluído"
                    else "✕"
                )

                titulo = item.get("titulo") or "Vídeo"
                formato = item.get("formato") or "—"
                data = item.get("data") or ""

                linha = (
                    f"{simbolo} {titulo}\n"
                    f"   {formato} | {data}\n\n"
                )

                self.lista_historico.insert(
                    "end",
                    linha
                )

        self.lista_historico.configure(state="disabled")

    # NOTIFICAÇÃO ------------------------------------------------------------

    def notificar(self, titulo, mensagem):

        try:

            from winotify import Notification

            Notification(
                app_id=APP_NAME,
                title=titulo,
                msg=mensagem[:200],
                duration="short"
            ).show()

        except Exception:
            pass

    # FECHAR APLICAÇÃO -------------------------------------------------------

    def fechar_aplicativo(self):

        if self.baixando:

            self.cancelamento.set()

            self.resultado.configure(
                text="Cancelando o download antes de fechar...",
                text_color=COR_LARANJA
            )

            self.after(300, self.fechar_aplicativo)
            return

        self.destroy()


# INICIAR --------------------------------------------------------------------

if __name__ == "__main__":

    janela = YouTubeDownloader()
    janela.mainloop()


