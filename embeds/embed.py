from flask import Flask, render_template, request, redirect, url_for
import discord
import asyncio
import json
import os

app = Flask(__name__)
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegúrate de que la carpeta de uploads exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Variable global para almacenar el resultado de la operación
result_message = None
result_type = None  # Puede ser "success" o "error"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/editor.html')
def editor_page():
    return render_template('editor.html')

@app.route('/send_embed', methods=['POST'])
def send_embed():
    global result_message, result_type

    try:
        # Obtén los datos del formulario
        token = request.form['token']
        channel_id = int(request.form['channel_id'])
        json_file = request.files['json_file']

        # Guarda temporalmente el archivo subido
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], json_file.filename)
        json_file.save(file_path)

        # Lee y parsea el JSON del archivo
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
                embeds = json_data["backups"][0]["messages"][0]["data"]["embeds"]
                print(f"Embeds encontrados: {embeds}")  # Depuración de embeds

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            result_message = "El archivo JSON no tiene la estructura esperada."
            result_type = "error"
            return redirect(url_for('send_embed_page'))

        # Configuración del bot de Discord
        intents = discord.Intents.default()
        client = discord.Client(intents=intents)

        async def send_embeds():
            try:
                print("Intentando iniciar el bot...")  # Depuración de inicio del bot
                await client.start(token)  # Inicia el bot
            except Exception as e:
                print(f"Error al iniciar el bot: {e}")
                result_message = "Ocurrió un error al iniciar el bot."
                result_type = "error"

        @client.event
        async def on_ready():
            print(f"Bot conectado como {client.user}")
            channel = client.get_channel(channel_id)

            if not channel:
                print(f"Canal no encontrado. ID del canal: {channel_id}")  # Depuración del canal
                await client.close()
                result_message = "Canal no encontrado."
                result_type = "error"
                return

            try:
                # Enviar todos los embeds
                for embed_data in embeds:
                    print(f"Enviando embed: {embed_data}")  # Depuración de embeds
                    embed = discord.Embed.from_dict(embed_data)
                    await channel.send(embed=embed)
                print("Embeds enviados correctamente.")
                await client.close()
                result_message = "Embeds enviados correctamente."
                result_type = "success"
            except Exception as e:
                print(f"Error al enviar los embeds: {e}")
                await client.close()
                result_message = "Ocurrió un error al enviar los embeds."
                result_type = "error"

        # Usamos asyncio.run() para iniciar el bot de manera correcta sin interferir con Flask
        asyncio.run(send_embeds())

    except Exception as e:
        print(f"Error: {e}")
        result_message = "Ocurrió un error al procesar la solicitud."
        result_type = "error"
        return redirect(url_for('send_embed_page'))

    return redirect(url_for('send_embed_page'))  # Asegurarse de retornar aquí

@app.route('/send_embed')
def send_embed_page():
    global result_message, result_type
    return render_template('send_embed.html', message=result_message, message_type=result_type)

if __name__ == '__main__':
    app.run(port=8000)
