from flask import Flask, request, render_template, jsonify, redirect, url_for
import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import threading

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_config', methods=['POST'])
def submit_config():
    try:
        # Obtener los datos del formulario
        token = request.form.get('token')
        channel_id = int(request.form.get('channel_id'))
        ticket_message = request.form.get('ticket_message')
        
        # Obtener la URL de la imagen
        image_url = request.form.get('image_url')
        
        # Obtener las opciones del desplegable (ahora como listas)
        dropdown_labels = request.form.getlist('dropdown_labels[]')
        dropdown_descriptions = request.form.getlist('dropdown_descriptions[]')
        dropdown_emojis = request.form.getlist('dropdown_emojis[]')

        # Depuración: Ver los valores recibidos
        print(f"Opciones del desplegable: {dropdown_labels}")
        print(f"Descripciones del desplegable: {dropdown_descriptions}")
        print(f"Emojis del desplegable: {dropdown_emojis}")

        if not dropdown_labels or any(option.strip() == "" for option in dropdown_labels):
            return jsonify({"message": "Error: No se proporcionaron opciones para el desplegable."})
        
        # Crear una instancia de Intents
        intents = discord.Intents.default()
        intents.messages = True  # Habilitar la lectura de mensajes

        # Iniciar el cliente de Discord con los intents
        bot = commands.Bot(command_prefix="!", intents=intents)

        @bot.event
        async def on_ready():
            channel = bot.get_channel(channel_id)
            
            # Cambiar esta línea para usar el mensaje ingresado
            embed = discord.Embed(
                description=ticket_message,  # Usamos el mensaje del formulario
                color=discord.Color.yellow()
            )
            
            if image_url:
                # Si se ha proporcionado una URL de imagen, añadirla al embed
                embed.set_image(url=image_url)

            # Crear dinámicamente las opciones del desplegable
            select_options = [
                discord.SelectOption(
                    label=label,
                    value=label.lower().replace(" ", "_"),
                    description=description,
                    emoji=emoji if emoji else None
                )
                for label, description, emoji in zip(dropdown_labels, dropdown_descriptions, dropdown_emojis)
            ]
            
            select = Select(
                placeholder="Selecciona una opción",
                min_values=1,
                max_values=1,
                options=select_options
            )
            
            async def select_callback(interaction: discord.Interaction):
                selected_value = select.values[0]
                guild = interaction.guild
                author = interaction.user
                category = discord.utils.get(guild.categories, name="Tickets")

                if not category:
                    category = await guild.create_category("Tickets")

                # Generar el número de ticket basado en el autor
                ticket_number = len([ch for ch in category.channels if ch.name.startswith(f"ticket-{author.name.lower()}")]) + 1
                ticket_channel = await category.create_text_channel(
                    f"ticket-{author.name.lower()}-{selected_value}-{ticket_number}",
                    overwrites={ 
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                    }
                )

                close_button = Button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger)

                async def close_callback(interaction: discord.Interaction):
                    if interaction.channel == ticket_channel:
                        await interaction.response.send_message("El ticket ha sido cerrado.", ephemeral=True)
                        await ticket_channel.delete()
                    else:
                        await interaction.response.send_message("Este no es el canal del ticket.", ephemeral=True)

                close_button.callback = close_callback

                ticket_view = View(timeout=None)
                ticket_view.add_item(close_button)

                # Enviar el mensaje al canal del ticket
                await ticket_channel.send(f"¡Hola {author.mention}! Enseguida alguien se ocupará de tu ticket. ¿Cuál es tu consulta?")
                embed_ticket = discord.Embed(description=" ", color=discord.Color.green())
                embed_ticket.add_field(
                    name="El soporte estará con usted en breve.",
                    value="Para cerrar este ticket, presiona el botón 🔒",
                    inline=False
                )

                await ticket_channel.send(embed=embed_ticket, view=ticket_view)
                await interaction.response.send_message(f"Se ha creado tu ticket para {selected_value} #{ticket_number}.", ephemeral=True)

            select.callback = select_callback

            # Enviar el mensaje con el select y los botones
            view = View(timeout=None)
            view.add_item(select)
            await channel.send(embed=embed, view=view)

        def run_bot():
            bot.run(token)

        # Crear un hilo para ejecutar el bot en paralelo
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.start()

        # Redirigir a result.html después de guardar la configuración
        return render_template('result.html', message="Configuración guardada correctamente.")
    
    except Exception as e:
        return jsonify({"message": f"Error: {e}"})

if __name__ == '__main__':
    app.run(debug=True)
