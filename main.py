import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio
import json
import os



intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=None, intents=intents)
tree = bot.tree

# Variables globales para votación
votacion_estado = {"activa": False, "canal_id": None, "mensaje_id": None}

# Conexión y tabla de base de datos
conn = sqlite3.connect("sanciones.db")
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS sanciones (
    user_id INTEGER,
    tipo TEXT,
    razon TEXT,
    responsable_id INTEGER,
    caso INTEGER
)""")
conn.commit()

c.execute('''
CREATE TABLE IF NOT EXISTS multas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    agente_id INTEGER,
    placa TEXT,
    motivo TEXT,
    monto REAL,
    estado TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS dni (
    user_id INTEGER PRIMARY KEY,
    nombres_apellidos TEXT,
    edad INTEGER,
    fecha_nacimiento TEXT,
    nacionalidad TEXT,
    sexo TEXT
)
''')
conn.commit()

c.execute('''
    CREATE TABLE IF NOT EXISTS prestamos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        labor TEXT,
        monto INTEGER,
        motivo TEXT,
        fecha_emision TEXT,
        fecha_pago TEXT,
        responsable_id INTEGER,
        nota_adicional TEXT,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()



# Función para contar sanciones/advertencias
def contar_registros(user_id, tipo):
    c.execute("SELECT COUNT(*) FROM sanciones WHERE user_id = ? AND tipo = ?", (user_id, tipo))
    return c.fetchone()[0]

# Función para verificar permisos
def tiene_permiso(interaction, comando):
    es_admin = interaction.user.guild_permissions.administrator
    rol_mod = discord.Object(id=1390915547373502564)
    if comando in ["advertir", "sancionar"]:
        return es_admin or rol_mod in interaction.user.roles
    elif comando == "banear":
        return es_admin
    return False

#Comando de advertencia
@bot.tree.command(name="advertir", description="Advierte a un usuario. Al llegar a 3 advertencias, se recomienda sancionar.")
@app_commands.describe(usuario="Usuario a advertir", razon="Motivo de la advertencia")
async def advertir(interaction: discord.Interaction, usuario: discord.Member, razon: str):
    if not interaction.user.guild_permissions.administrator and 1348600963128102952 not in [r.id for r in interaction.user.roles] and 1390915547373502564 not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)

    c.execute("SELECT COUNT(*) FROM sanciones WHERE user_id = ? AND tipo = ?", (usuario.id, "Advertencia"))
    advertencias = c.fetchone()[0]

    if advertencias >= 3:
        return await interaction.response.send_message("⚠️ Este usuario ya tiene más de 3 advertencias, ¡sanciónalo!", ephemeral=True)

    c.execute("INSERT INTO sanciones (user_id, tipo, razon, responsable_id, caso) VALUES (?, ?, ?, ?, ?)",
              (usuario.id, "Advertencia", razon, interaction.user.id, advertencias + 1))
    conn.commit()

    embed = discord.Embed(title="⚠️ ADVERTENCIA", color=discord.Color.orange())
    embed.set_thumbnail(url="https://cdn.discordapp.com/icons/1333507237112451112/13071077db419d613b41794815fb906c.png?size=4096")
    embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
    embed.add_field(name="📄 Razón", value=razon, inline=True)
    embed.add_field(name="👮 Responsable", value=interaction.user.mention, inline=True)
    embed.add_field(name="📌 Caso", value=f"{advertencias + 1}", inline=True)

    await interaction.response.send_message(embed=embed)


#Comando sancionar
@bot.tree.command(name="sancionar", description="Sanciona a un usuario.")
@app_commands.describe(usuario="Usuario a sancionar", razon="Motivo de la sanción")
async def sancionar(interaction: discord.Interaction, usuario: discord.Member, razon: str):
    if not interaction.user.guild_permissions.administrator and 1348600963128102952 not in [r.id for r in interaction.user.roles] and 1390915547373502564 not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)

    c.execute("SELECT COUNT(*) FROM sanciones WHERE tipo = 'Sanción'")
    caso = c.fetchone()[0] + 1

    c.execute("INSERT INTO sanciones (user_id, tipo, razon, responsable_id, caso) VALUES (?, ?, ?, ?, ?)",
              (usuario.id, "Sanción", razon, interaction.user.id, caso))
    conn.commit()

    embed = discord.Embed(title="🚨 SANCIÓN APLICADA", color=discord.Color.red())
    embed.set_thumbnail(url="https://cdn.discordapp.com/icons/1333507237112451112/13071077db419d613b41794815fb906c.png?size=4096")
    embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
    embed.add_field(name="📄 Razón", value=razon, inline=True)
    embed.add_field(name="👮 Responsable", value=interaction.user.mention, inline=True)
    embed.add_field(name="📌 Caso", value=str(caso), inline=True)

    # Botón de apelar
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Apelar", style=discord.ButtonStyle.link, url="https://discord.com/channels/1390915546865729677/1390915549260943491"))

    await interaction.response.send_message(embed=embed, view=view)


#Comando banear 
@tree.command(name="banear", description="Banea a un usuario.")
@app_commands.describe(usuario="Usuario a banear", razon="Razón del baneo")
async def banear(interaction: discord.Interaction, usuario: discord.Member, razon: str):
    if not tiene_permiso(interaction, "banear"):
        return await interaction.response.send_message("No tienes permiso.", ephemeral=True)

    try:
        await usuario.ban(reason=razon)
    except:
        return await interaction.response.send_message("No pude banear al usuario. ¿Tengo permisos suficientes?", ephemeral=True)

    embed = discord.Embed(title="⛔ USUARIO BANEADO", color=discord.Color.red())
    embed.set_thumbnail(url="https://cdn.discordapp.com/icons/1333507237112451112/13071077db419d613b41794815fb906c.png?size=4096")
    embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
    embed.add_field(name="🧑 Responsable", value=interaction.user.mention, inline=True)
    embed.add_field(name="📝 Razón", value=razon, inline=False)
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Apelar", url="https://discord.com/channels/1206039045118099466/1325249521017688064"))
    await interaction.response.send_message(embed=embed, view=view)


# Reiniciar Warn´s
@bot.tree.command(name="reiniciar-wars", description="Reinicia todas las sanciones del servidor.")
async def reiniciar_wars(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo los administradores pueden usar este comando.", ephemeral=True)

    c.execute("DELETE FROM sanciones WHERE tipo = ?", ("sancion",))
    conn.commit()
    await interaction.response.send_message("🔁 Todas las **sanciones** han sido reiniciadas.")

# Reiniviar adv
@bot.tree.command(name="reiniciar-adv", description="Reinicia todas las advertencias del servidor.")
async def reiniciar_adv(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Solo los administradores pueden usar este comando.", ephemeral=True)

    c.execute("DELETE FROM sanciones WHERE tipo = ?", ("advertencia",))
    conn.commit()
    await interaction.response.send_message("🔁 Todas las **advertencias** han sido reiniciadas.")

#DNI
# Comando: /crear-dni
@bot.tree.command(name="crear-dni", description="Registra tu cédula de identidad")
@app_commands.describe(
    nombres_apellidos="Escribe tus nombres y apellidos completos",
    edad="Debes tener más de 18 años",
    fecha_nacimiento="Formato: dd/mm/yyyy",
    nacionalidad="Selecciona tu nacionalidad",
    sexo="Selecciona tu sexo"
)
@app_commands.choices(
    nacionalidad=[
        discord.app_commands.Choice(name="Ecuatoriano", value="Ecuatoriano"),
        discord.app_commands.Choice(name="Extranjero", value="Extranjero")
    ],
    sexo=[
        discord.app_commands.Choice(name="Masculino", value="Masculino"),
        discord.app_commands.Choice(name="Femenino", value="Femenino")
    ]
)
async def crear_dni(interaction: discord.Interaction,
                    nombres_apellidos: str,
                    edad: int,
                    fecha_nacimiento: str,
                    nacionalidad: discord.app_commands.Choice[str],
                    sexo: discord.app_commands.Choice[str]):

    if edad < 18:
        await interaction.response.send_message("❌ Debes tener más de 18 años para registrar tu DNI.", ephemeral=True)
        return

    c.execute(
        "REPLACE INTO dni (user_id, nombres_apellidos, edad, fecha_nacimiento, nacionalidad, sexo) VALUES (?, ?, ?, ?, ?, ?)",
        (interaction.user.id, nombres_apellidos, edad, fecha_nacimiento, nacionalidad.value, sexo.value)
    )
    conn.commit()

    await interaction.response.send_message("✅ DNI registrado correctamente.", ephemeral=True)


# Comando: /ver-dni
@bot.tree.command(name="ver-dni", description="Muestra tu DNI o el de otro usuario")
@app_commands.describe(usuario="Usuario del cual quieres ver el DNI (opcional)")
async def ver_dni(interaction: discord.Interaction, usuario: discord.User = None):
    target = usuario or interaction.user

    c.execute("SELECT nombres_apellidos, edad, fecha_nacimiento, nacionalidad, sexo FROM dni WHERE user_id = ?", (target.id,))
    resultado = c.fetchone()

    if not resultado:
        await interaction.response.send_message("❌ Este usuario no tiene un DNI registrado.", ephemeral=True)
        return

    nombres_apellidos, edad, fecha_nacimiento, nacionalidad, sexo = resultado

    embed = discord.Embed(title="🪪| CEDULA", color=discord.Color.red())
    embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
    embed.add_field(name="Nombres y Apellidos", value=nombres_apellidos, inline=False)
    embed.add_field(name="Edad", value=str(edad), inline=False)
    embed.add_field(name="Fecha de nacimiento", value=fecha_nacimiento, inline=False)
    embed.add_field(name="Nacionalidad", value=nacionalidad, inline=False)
    embed.add_field(name="Sexo", value=sexo, inline=False)
    embed.add_field(name="Número de DNI", value=str(target.id), inline=False)
    embed.set_footer(
        text="Si quieres eliminar tu dni aplica el comando /eliminar-dni",
        icon_url="https://cdn.discordapp.com/icons/1206039045118099466/bc1c633d13a146ff4eb96560ecffc168.png?size=4096"
    )

    await interaction.response.send_message(embed=embed)


# Comando: /eliminar-dni
@bot.tree.command(name="eliminar-dni", description="Elimina el DNI de un usuario (solo para rol autorizado)")
@app_commands.describe(usuario="Usuario cuyo DNI deseas eliminar")
async def eliminar_dni(interaction: discord.Interaction, usuario: discord.User):
    if 1348804433286271046 not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
        return

    c.execute("SELECT * FROM dni WHERE user_id = ?", (usuario.id,))
    if not c.fetchone():
        await interaction.response.send_message("❌ Este usuario no tiene un DNI registrado.", ephemeral=True)
        return

    c.execute("DELETE FROM dni WHERE user_id = ?", (usuario.id,))
    conn.commit()

    await interaction.response.send_message(f"✅ El DNI de {usuario.mention} ha sido eliminado.", ephemeral=True)

    canal_publico = bot.get_channel(1206039049547288637)
    if canal_publico:
        await canal_publico.send(f"📢 {usuario.mention}, tu DNI fue eliminado. Por favor crea uno nuevo usando `/crear-dni`.")

    canal_logs = bot.get_channel(1397310794508537946)
    if canal_logs:
        embed = discord.Embed(title="🗑️ ELIMINACIÓN DE DNI", color=discord.Color.red())
        embed.add_field(name="👮 Responsable", value=interaction.user.mention, inline=False)
        embed.add_field(name="👤 Usuario afectado", value=usuario.mention, inline=False)
        embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else usuario.default_avatar.url)
        embed.set_footer(text="Registro de eliminación de DNI")
        await canal_logs.send(embed=embed)


#/multar
@bot.tree.command(name="multar", description="Aplica una multa de tránsito a un usuario.")
@app_commands.describe(
    agente="Menciónate a ti mismo como agente",
    usuario="Usuario al que se le aplicará la multa",
    placa="Placa del vehículo multado",
    motivo="Motivo de la multa",
    monto="Valor de la multa en dólares"
)
async def multar(interaction: discord.Interaction,
                 agente: discord.Member,
                 usuario: discord.Member,
                 placa: str,
                 motivo: str,
                 monto: float):

    # Verificar permisos - Owner o roles autorizados
    if not interaction.user.guild_permissions.administrator and 1390915547335753752 not in [r.id for r in interaction.user.roles] and 1390915547335753752 not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
        return

    # Guardar en base de datos
    c.execute('''
        INSERT INTO multas (user_id, agente_id, placa, motivo, monto, estado)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (usuario.id, agente.id, placa, motivo, monto, "Emisión"))
    conn.commit()

    # Asignar rol al multado
    rol_multado = interaction.guild.get_role(1348364787175784528)
    if rol_multado:
        try:
            await usuario.add_roles(rol_multado)
        except:
            pass  # Por si no se puede asignar

    # Crear embed
    embed = discord.Embed(title="🚨 | MULTA DE TRÁNSITO", color=discord.Color.red())
    embed.set_thumbnail(url="https://conocimiento.blob.core.windows.net/conocimiento/Manuales/Carta_Porte/drex_multas_custom_3.png")
    embed.add_field(name="👮 Agente", value=agente.mention, inline=False)
    embed.add_field(name="👤 Multado", value=usuario.mention, inline=False)
    embed.add_field(name="🚗 Placa", value=placa, inline=False)
    embed.add_field(name="💬 Motivo", value=motivo, inline=False)
    embed.add_field(name="💰 Monto", value=f"${monto:.2f}", inline=False)
    embed.add_field(name="📄 Estado", value="Emisión", inline=False)
    embed.set_footer(
        text="Si no está de acuerdo consultarlo en las oficinas de la CTE.",
        icon_url="https://www.gob.ec/sites/default/files/styles/medium/public/2018-09/CTG.gif?itok=XthsG_y_"
    )

    # Botón "Pagar"
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Pagar",
        url="https://discord.com/channels/1390915546865729677/1398809992743882773",
        style=discord.ButtonStyle.link
    ))

    await interaction.response.send_message(embed=embed, view=view)

#ver-multa
@bot.tree.command(name="ver-multas", description="Muestra tus multas o las de otro usuario.")
@app_commands.describe(usuario="(Opcional) Usuario del que deseas ver las multas")
async def ver_multas(interaction: discord.Interaction, usuario: discord.Member = None):
    target = usuario or interaction.user

    # Consultar multas de la base de datos
    c.execute("SELECT agente_id, placa, motivo, monto, estado FROM multas WHERE user_id = ?", (target.id,))
    multas = c.fetchall()

    if not multas:
        await interaction.response.send_message("✅ Este usuario no tiene multas registradas.", ephemeral=True)
        return

    embeds = []
    for i, (agente_id, placa, motivo, monto, estado) in enumerate(multas, start=1):
        embed = discord.Embed(title=f"🚨 Multa #{i}", color=discord.Color.red())
        embed.set_thumbnail(url="https://conocimiento.blob.core.windows.net/conocimiento/Manuales/Carta_Porte/drex_multas_custom_3.png")
        embed.add_field(name="👮 Agente", value=f"<@{agente_id}>", inline=False)
        embed.add_field(name="🚗 Placa", value=placa, inline=False)
        embed.add_field(name="💬 Motivo", value=motivo, inline=False)
        embed.add_field(name="💰 Monto", value=f"${monto:.2f}", inline=False)
        embed.add_field(name="📄 Estado", value=estado, inline=False)
        embed.set_footer(
            text="Si no está de acuerdo consultarlo en las oficinas de la CTE.",
            icon_url="https://www.gob.ec/sites/default/files/styles/medium/public/2018-09/CTG.gif?itok=XthsG_y_"
        )
        embeds.append(embed)

    # Enviar embed único o paginación
    if len(embeds) == 1:
        await interaction.response.send_message(embed=embeds[0], ephemeral=True)
    else:
        class Paginacion(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.index = 0

            @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.primary)
            async def anterior(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                if self.index > 0:
                    self.index -= 1
                    await interaction_button.response.edit_message(embed=embeds[self.index], view=self)

            @discord.ui.button(label="➡️ Siguiente", style=discord.ButtonStyle.primary)
            async def siguiente(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                if self.index < len(embeds) - 1:
                    self.index += 1
                    await interaction_button.response.edit_message(embed=embeds[self.index], view=self)

        await interaction.response.send_message(embed=embeds[0], view=Paginacion(), ephemeral=True)


# Clase de botones aceptar / negar
class BotonesVerificacion(discord.ui.View):
    def __init__(self, user: discord.Member, respuestas: dict):
        super().__init__(timeout=None)
        self.user = user
        self.respuestas = respuestas

    @discord.ui.button(label="✅ Aceptar", style=discord.ButtonStyle.success, custom_id="aceptar_verificacion")
    async def aceptar(self, interaction: discord.Interaction, button: discord.ui.Button):
        roles_dar = [1390915546865729682, 1390915547226705990]
        rol_quitar = 1390915546865729683

        # Get member object from guild
        member = interaction.guild.get_member(self.user.id)
        if not member:
            await interaction.response.send_message("❌ Error: Usuario no encontrado en el servidor.", ephemeral=True)
            return

        for rol_id in roles_dar:
            rol = interaction.guild.get_role(rol_id)
            if rol:
                await member.add_roles(rol)
        rol = interaction.guild.get_role(rol_quitar)
        if rol:
            await member.remove_roles(rol)

        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        await interaction.channel.send(f"✅ {interaction.user.mention} aceptó a {self.user.mention}")

        canal_logs = bot.get_channel(1398718830771179551)
        if canal_logs:
            await canal_logs.send(f"✅ {interaction.user.mention} aceptó a {self.user.mention}")

    @discord.ui.button(label="❌ Negar", style=discord.ButtonStyle.danger, custom_id="negar_verificacion")
    async def negar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if 1390915547373502558 not in [r.id for r in interaction.user.roles] and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ No tienes permiso para negar verificaciones.", ephemeral=True)

        modal = ModalNegacion(self.user, self.respuestas, interaction.user)
        await interaction.response.send_modal(modal)


# Modal para negar verificación
class ModalNegacion(discord.ui.Modal, title="Denegar Verificación"):
    motivo = discord.ui.TextInput(label="Motivo de rechazo", style=discord.TextStyle.short)
    nota = discord.ui.TextInput(label="Nota adicional", style=discord.TextStyle.paragraph, required=False)

    def __init__(self, user, respuestas, responsable):
        super().__init__()
        self.user = user
        self.respuestas = respuestas
        self.responsable = responsable

    async def on_submit(self, interaction: discord.Interaction):
        # Responder primero a la interacción del modal
        await interaction.response.defer()

        embed = discord.Embed(title="❌ Verificación Denegada", color=discord.Color.red())
        embed.set_thumbnail(url="https://media.istockphoto.com/id/1131230925/es/vector/marcas-de-verificaci%C3%B3n-icono-de-cruz-roja-simple-vector.jpg?s=612x612&w=0&k=20&c=l5B95lRQ7TSik_Ou14ldJo35fy9REg7bQp6EH3zLt3M=")
        for campo, valor in self.respuestas.items():
            embed.add_field(name=campo, value=valor, inline=False)
        embed.add_field(name="📌 Motivo de rechazo", value=self.motivo.value, inline=False)
        if self.nota.value:
            embed.add_field(name="📝 Nota adicional", value=self.nota.value, inline=False)

        try:
            await self.user.send(embed=embed)
        except:
            pass

        # Desactivar botones del mensaje original
        view = discord.ui.View()
        for item in self.children:
            item.disabled = True
            view.add_item(item)

        # Obtener el mensaje original desde el canal
        canal_verificacion = bot.get_channel(1390915553723420768)
        if canal_verificacion:
            async for message in canal_verificacion.history(limit=50):
                if message.embeds and message.embeds[0].title == "📋 Solicitud de Verificación":
                    if self.user.mention in message.embeds[0].fields[0].value:
                        for item in message.components[0].children:
                            item.disabled = True
                        await message.edit(view=discord.ui.View.from_message(message))
                        break

        await interaction.followup.send(f"❌ {self.responsable.mention} denegó a {self.user.mention}")

        canal_logs = bot.get_channel(1398718830771179551)
        if canal_logs:
            await canal_logs.send(f"❌ {self.responsable.mention} denegó a {self.user.mention} | Motivo: {self.motivo.value}")


#Sistema de verificación
@bot.tree.command(name="verificación", description="Envía tu solicitud de verificación")
@app_commands.describe(
    usuario_roblox="Tu nombre de usuario de Roblox",
    nombre_ic="Tu nombre y apellido IC",
    conociste="¿Cómo conociste el servidor?",
    respeto="¿Sabes que debes mantener el respeto a nivel general?",
    link="Pega aquí el link de tu perfil de Roblox"
)
@app_commands.choices(
    respeto=[
        discord.app_commands.Choice(name="Sí", value="Sí"),
        discord.app_commands.Choice(name="No", value="No")
    ]
)
async def verificacion(interaction: discord.Interaction,
                       usuario_roblox: str,
                       nombre_ic: str,
                       conociste: str,
                       respeto: discord.app_commands.Choice[str],
                       link: str):

    try:
        canal_destino = bot.get_channel(1390915553723420768)
        if not canal_destino:
            await interaction.response.send_message("❌ Error: Canal de verificación no encontrado. Contacta a un administrador.", ephemeral=True)
            print(f"Error: Canal {1390915553723420768} no encontrado")
            return

        respuestas = {
            "Usuario de Roblox": usuario_roblox,
            "Nombre y Apellido IC": nombre_ic,
            "¿Cómo conoció el servidor?": conociste,
            "¿Mantendrá el respeto?": respeto.value,
            "Link de perfil": link
        }

        embed = discord.Embed(title="📋 Solicitud de Verificación", color=discord.Color.red())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=False)

        for campo, valor in respuestas.items():
            embed.add_field(name=campo, value=valor, inline=False)

        view = BotonesVerificacion(interaction.user, respuestas)
        await canal_destino.send(content=f"<@&1390915547373502564> se ha enviado una verificación.", embed=embed, view=view)

        await interaction.response.send_message("✅ Tu verificación ha sido enviada. Espera que un staff te lo revise y te acepte.", ephemeral=True)
        print(f"Verificación enviada por {interaction.user} ({interaction.user.id})")

    except Exception as e:
        print(f"Error en comando verificación: {e}")
        try:
            await interaction.response.send_message("❌ Error al enviar la verificación. Contacta a un administrador.", ephemeral=True)
        except:
            await interaction.followup.send("❌ Error al enviar la verificación. Contacta a un administrador.", ephemeral=True)


# Comando: /apertura
@bot.tree.command(name="apertura", description="Inicia una votación para abrir el servidor RP.")
async def apertura(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator and 1390915547385827451 not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
        return
    if interaction.channel.id not in [1398029993677684806, 1390915553723420764]:
        await interaction.response.send_message("❌ Este comando solo se puede usar en los canales autorizados.", ephemeral=True)
        return
    embed = discord.Embed(
        title="¡VOTACIÓN DE APERTURA!",
        description=f"**Staff:** {interaction.user.mention}\n\nMuy buenas a todos los usuarios, si quieren rolear y divertirse y pasarla muy bien voten \U0001F7E2 caso contrario \U0001F534, se les recuerde que para abrir el servidor se espera al menos 7 votos\n\n\U0001F5F3\uFE0F Votos esperados: 7/7\n\U0001F5F3\uFE0F Votos: 0/7\n\n\u203C\uFE0F**Recordatorio**\nSe les recuerda que votar y no unirse es motivo de sanción",
        color=discord.Color.red()
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1390915553723420764/1398089110618640577/Sin_titulo.jpg?ex=688611b3&is=6884c033&hm=8cb075c8aaadb7e496a1951ee98b0d787e1e4fc78ecf18243dd0c94ec759bf4c&")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1365154065708875857/1398548305948049518/icono_athaualpa.png?ex=68866bdb&is=68851a5b&hm=7332f5e26e74521d4957a6cc0c175f3badc9b0ef85170a95aae16531a702159e&")
    embed.set_footer(text="Derechos reservados de UIO ATAHUALPA RP | ER:LC", icon_url="https://cdn.discordapp.com/attachments/1397851859036930088/1398786910150983690/IMG_5793.png?ex=6886a153&is=68854fd3&hm=0495d15cbdc1cb8ca892eabbb0f33aef5bb62d502410b54c663a984da8232710&")
    mensaje = await interaction.channel.send(content="<@&1390915547226705990>", embed=embed)
    await mensaje.add_reaction("\U0001F7E2")
    await mensaje.add_reaction("\U0001F534")
    with open("votacion.json", "w") as f:
        json.dump({"canal_id": interaction.channel.id, "mensaje_id": mensaje.id}, f)
    votacion_estado["activa"] = True
    votacion_estado["canal_id"] = interaction.channel.id
    votacion_estado["mensaje_id"] = mensaje.id
    await interaction.response.send_message("✅ Votación de apertura enviada.", ephemeral=True)

    async def actualizar_votos():
        while votacion_estado["activa"]:
            try:
                mensaje_actualizado = await interaction.channel.fetch_message(mensaje.id)
                reacciones = {str(r.emoji): r.count - 1 for r in mensaje_actualizado.reactions}
                votos_si = reacciones.get("\U0001F7E2", 0)
                embed.description = f"**Staff:** {interaction.user.mention}\n\nMuy buenas a todos los usuarios, si quieren rolear y divertirse y pasarla muy bien voten \U0001F7E2 caso contrario \U0001F534, se les recuerde que para abrir el servidor se espera al menos 7 votos\n\n\U0001F5F3\uFE0F Votos esperados: 7/7\n\U0001F5F3\uFE0F Votos: {votos_si}/7\n\n\u203C\uFE0F**Recordatorio**\nSe les recuerda que votar y no unirse es motivo de sanción"
                await mensaje.edit(embed=embed)
                await asyncio.sleep(10)
            except:
                break
    bot.loop.create_task(actualizar_votos())


# Comando: /abrir-server
@bot.tree.command(name="abrir-server", description="Abre el servidor luego de la votación")
async def abrir_server(interaction: discord.Interaction):
    if not interaction.channel.id in [1398029993677684806, 1390915553723420764]:
        return await interaction.response.send_message("❌ Este comando solo puede usarse en los canales permitidos.", ephemeral=True)
    if 1390915547385827451 not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
    if not votacion_estado["activa"]:
        return await interaction.response.send_message("❌ No hay una votación activa.", ephemeral=True)

    # Responder primero a la interacción
    await interaction.response.send_message("✅ Servidor abierto.", ephemeral=True)

    try:
        canal = bot.get_channel(votacion_estado["canal_id"])
        mensaje = await canal.fetch_message(votacion_estado["mensaje_id"])
        reacciones = [r for r in mensaje.reactions if str(r.emoji) == "\U0001F7E2"]
        if not reacciones:
            return await interaction.followup.send("❌ No se encontraron votos 🟢.", ephemeral=True)
        usuarios = [user async for user in reacciones[0].users() if not user.bot]
    except:
        return await interaction.followup.send("❌ No se encontró una votación activa.", ephemeral=True)

    texto_votantes = "\n".join([f"{u.mention}" for u in usuarios]) or "Nadie votó."
    embed = discord.Embed(description=(
        f"Abierto por: {interaction.user.mention}\n\n"
        "📣 Todos los que participaron en la votación tendrán 15 minutos para unirse.\n\n"
        "🗳️ Votantes:\n"
        f"{texto_votantes}\n\n"
        "🔓CÓDIGO: ECU\n\n"
        "‼️Recuerda:\n"
        "[Leer Normativas de RP](https://discord.com/channels/ID/1390915548690382977)\n"
        "[Leer Conceptos de RP](https://discord.com/channels/ID/1390915548690382978)\n"
        "[Ver las Zonas Seguras](https://discord.com/channels/ID/1390915549260943482)\n\n"
        "‼️Para una experiencia más realista:\n"
        "[Leer las Reglas de Avatar](https://discord.com/channels/ID/1390915548690382979)\n"
        "[Mapa](https://discord.com/channels/ID/1390915549260943483)"
    ), color=discord.Color.red())
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1365154065708875857/1398548305948049518/icono_athaualpa.png?ex=68866bdb&is=68851a5b&hm=7332f5e26e74521d4957a6cc0c175f3badc9b0ef85170a95aae16531a702159e&")
    embed.set_footer(text="Derechos reservados de UIO ATAHUALPA RP | ER:LC", icon_url="https://cdn.discordapp.com/attachments/1397851859036930088/1398786910150983690/IMG_5793.png?ex=6886a153&is=68854fd3&hm=0495d15cbdc1cb8ca892eabbb0f33aef5bb62d502410b54c663a984da8232710&")
    await interaction.channel.send(content="<@&1390915547226705990>", embed=embed)
    votacion_estado["activa"] = False


@bot.tree.command(name="cerrar-server", description="Cierra el servidor")
async def cerrar_server(interaction: discord.Interaction):
    if not interaction.channel.id in [1398029993677684806, 1390915553723420764]:
        return await interaction.response.send_message("❌ Este comando solo puede usarse en los canales permitidos.", ephemeral=True)
    if 1390915547385827451 not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
    embed = discord.Embed(
        title="SERVIDOR CERRADO",
        description=(
            f"Cerrado por: {interaction.user.mention}\n\n"
            "Muy buenas a todos, el servidor acaba de ser cerrado, muchas gracias por rolear, ¡Nos vemos en la próxima apertura!.\n\n"
            "🔐 Recuerda\nNo te unas al juego mientras este cerrado, esto provoca sospechas al Staff por ciertos motivos."
        ),
        color=discord.Color.red()
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1254918636007850198/1332820107784753224/standard_1.gif?ex=688695f4&is=68854474&hm=4d15052754842dc25ac06254589ee505c3e553304d926295f49401a25f2f29b1&")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1365154065708875857/1398548305948049518/icono_athaualpa.png?ex=68866bdb&is=68851a5b&hm=7332f5e26e74521d4957a6cc0c175f3badc9b0ef85170a95aae16531a702159e&")
    embed.set_footer(text="Derechos reservados de UIO ATAHUALPA RP | ER:LC", icon_url="https://cdn.discordapp.com/attachments/1397851859036930088/1398786910150983690/IMG_5793.png?ex=6886a153&is=68854fd3&hm=0495d15cbdc1cb8ca892eabbb0f33aef5bb62d502410b54c663a984da8232710&")
    await interaction.channel.send(content="<@&1390915547226705990>", embed=embed)
    try:
        import os
        if os.path.exists("votacion.json"):
            os.remove("votacion.json")
            print("✅ Registro de votación eliminado")
        votacion_estado["activa"] = False
    except Exception as e:
        print(f"Error al eliminar votacion.json: {e}")
    await interaction.response.send_message("✅ Servidor cerrado.", ephemeral=True)


#Anti-link maliciosos
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Verificar que estamos en un servidor (no en DMs)
    if not message.guild:
        return

    links_prohibidos = ["discordapp.com/invite/", "discord.gg/", "t.me/", "https://t.me/+"]

    # Excluir administradores del filtro de enlaces
    if message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return

    if any(link in message.content for link in links_prohibidos):
        try:
            await message.delete()
            await message.channel.send(
                f"🚫 {message.author.mention}, no está permitido enviar enlaces de invitación.",
                delete_after=6
            )
        except discord.Forbidden:
            print(f"No tengo permisos para eliminar mensaje de {message.author}")

    await bot.process_commands(message)

@bot.tree.command(name="ver-sanciones", description="Muestra las sanciones de un usuario")
@app_commands.describe(usuario="Usuario del cual quieres ver las sanciones")
async def ver_sanciones(interaction: discord.Interaction, usuario: discord.Member):
    # Verificar permisos - Solo staff autorizado puede ver sanciones
    if not interaction.user.guild_permissions.administrator and 1348600963128102952 not in [r.id for r in interaction.user.roles] and 1390915547373502564 not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)
        return

    # Consultar sanciones de la base de datos
    c.execute("SELECT tipo, razon, responsable_id, caso FROM sanciones WHERE user_id = ? ORDER BY caso DESC", (usuario.id,))
    sanciones = c.fetchall()

    if not sanciones:
        await interaction.response.send_message(f"✅ {usuario.mention} no tiene sanciones registradas.", ephemeral=True)
        return

    # Contar advertencias y sanciones
    advertencias = sum(1 for s in sanciones if s[0] == "Advertencia")
    sanciones_count = sum(1 for s in sanciones if s[0] == "Sanción")

    # Crear embed principal
    embed = discord.Embed(
        title="📋 HISTORIAL DE SANCIONES",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=usuario.display_avatar.url)
    embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
    embed.add_field(name="⚠️ Advertencias", value=str(advertencias), inline=True)
    embed.add_field(name="🚨 Sanciones", value=str(sanciones_count), inline=True)

    # Crear embeds individuales para cada sanción
    embeds = [embed]
    for i, (tipo, razon, responsable_id, caso) in enumerate(sanciones[:10], start=1):  # Limitar a 10 sanciones
        sancion_embed = discord.Embed(
            title=f"📌 {tipo} #{caso}",
            color=discord.Color.orange() if tipo == "Advertencia" else discord.Color.red()
        )
        sancion_embed.add_field(name="📄 Razón", value=razon, inline=False)
        sancion_embed.add_field(name="👮 Responsable", value=f"<@{responsable_id}>", inline=False)
        sancion_embed.set_footer(text=f"Sanción {i} de {len(sanciones)}")
        embeds.append(sancion_embed)

    # Si hay múltiples sanciones, usar paginación
    if len(embeds) > 1:
        class PaginacionSanciones(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
                self.index = 0

            @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.primary)
            async def anterior(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                if self.index > 0:
                    self.index -= 1
                    await interaction_button.response.edit_message(embed=embeds[self.index], view=self)

            @discord.ui.button(label="➡️ Siguiente", style=discord.ButtonStyle.primary)
            async def siguiente(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                if self.index < len(embeds) - 1:
                    self.index += 1
                    await interaction_button.response.edit_message(embed=embeds[self.index], view=self)

            @discord.ui.button(label="🏠 Inicio", style=discord.ButtonStyle.secondary)
            async def inicio(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                self.index = 0
                await interaction_button.response.edit_message(embed=embeds[self.index], view=self)

        await interaction.response.send_message(embed=embeds[0], view=PaginacionSanciones(), ephemeral=True)
    else:
        await interaction.response.send_message(embed=embeds[0], ephemeral=True)



    @bot.tree.command(name="scan-enlaces", description="Escanea mensajes anteriores en busca de enlaces prohibidos")
    @app_commands.checks.has_permissions(administrator=True)
    async def scan_enlaces(interaction: discord.Interaction, limite: int = 100):
        await interaction.response.send_message("🔍 Escaneando mensajes...", ephemeral=True)
        canales = interaction.guild.text_channels
        ID_AUTORIZADO = 1201985923605340235
        links_prohibidos = ["discordapp.com/invite/", "discord.gg/", "t.me/", "https://t.me/+"]
        eliminados = 0

        for canal in canales:
            try:
                async for msg in canal.history(limit=limite):
                    if any(link in msg.content for link in links_prohibidos) and msg.author.id != ID_AUTORIZADO:
                        await msg.delete()
                        eliminados += 1
            except Exception as e:
                print(f"Error en canal {canal.name}: {e}")

        await interaction.followup.send(f"✅ Escaneo completo. Mensajes eliminados: {eliminados}")

#Multas-generales
@bot.tree.command(name="multas-generales", description="Muestra el total de multas por usuario con opción a recordarlas")
async def multas_generales(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator and 1390915547335753752 not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ No tienes permiso para usar este comando.", ephemeral=True)

    # Traer todas las multas agrupadas
    c.execute("SELECT user_id, monto, estado FROM multas")
    registros = c.fetchall()

    if not registros:
        return await interaction.response.send_message("✅ No hay multas registradas.", ephemeral=True)

    # Organizar datos por usuario
    datos = {}
    for user_id, monto, estado in registros:
        uid = str(user_id)
        if uid not in datos:
            datos[uid] = {"cantidad": 0, "total": 0, "pendientes": 0}
        datos[uid]["cantidad"] += 1
        datos[uid]["total"] += monto
        if estado == "Emisión":
            datos[uid]["pendientes"] += 1

    # Crear embed resumen
    embed = discord.Embed(title="📊 MULTAS GENERALES", color=discord.Color.red())
    embed.set_thumbnail(url="https://conocimiento.blob.core.windows.net/conocimiento/Manuales/Carta_Porte/drex_multas_custom_3.png")

    for user_id, info in datos.items():
        embed.add_field(
            name=f"👤 <@{user_id}>",
            value=f"Multas: `{info['cantidad']}` | 💰 Total: `${info['total']:.2f}` | 🕒 Pendientes: `{info['pendientes']}`",
            inline=False
        )

    # Botón para recordar
    class RecordarView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=300)  # 5 minutos de timeout

        @discord.ui.button(label="📩 Recordar", style=discord.ButtonStyle.danger)
        async def recordar(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            try:
                # Verificar si la interacción ya fue respondida
                if interaction_btn.response.is_done():
                    return

                # Responder inmediatamente para evitar timeout
                await interaction_btn.response.defer(ephemeral=True)

                canal = bot.get_channel(1398809992743882773)
                if not canal:
                    return await interaction_btn.followup.send("❌ Canal no encontrado.", ephemeral=True)

                embed_recordatorio = discord.Embed(title="📢 PAGAR MULTAS", color=discord.Color.red())
                embed_recordatorio.set_thumbnail(url="https://conocimiento.blob.core.windows.net/conocimiento/Manuales/Carta_Porte/drex_multas_custom_3.png")

                descripcion = ""
                fallos = 0

                for user_id, info in datos.items():
                    if info["pendientes"] > 0:
                        descripcion += f"<@{user_id}> → 💰 **${info['total']:.2f}** en multas\n"
                        try:
                            user = await bot.fetch_user(int(user_id))
                            await user.send(embed=discord.Embed(
                                title="📬 RECORDATORIO DE MULTAS",
                                description=f"Tienes **{info['pendientes']}** multas pendientes por un total de **${info['total']:.2f}**.\nPor favor regulariza tu situación lo antes posible.",
                                color=discord.Color.red()
                            ))
                        except:
                            fallos += 1

                if descripcion:
                    embed_recordatorio.description = descripcion
                    await canal.send(embed=embed_recordatorio)

                msg = "✅ Recordatorio enviado."
                if fallos > 0:
                    msg += f" ⚠️ No se pudo enviar MD a {fallos} usuario(s)."

                await interaction_btn.followup.send(msg, ephemeral=True)

            except Exception as e:
                print(f"Error en recordar button: {e}")
                try:
                    if not interaction_btn.response.is_done():
                        await interaction_btn.response.send_message("❌ Error al procesar la solicitud.", ephemeral=True)
                    else:
                        await interaction_btn.followup.send("❌ Error al procesar la solicitud.", ephemeral=True)
                except:
                    pass

    await interaction.response.send_message(embed=embed, view=RecordarView())

#Sistema de prestamos
@bot.tree.command(name="prestamo", description="Solicita un préstamo indicando la labor y el motivo.")
@app_commands.describe(
    usuario="Menciona al usuario que recibirá el préstamo (usualmente tú mismo).",
    labor="Etiqueta a tu rol de trabajo, si eres ciudadano al rol ciudadano.",
    monto="Monto a solicitar (máximo 60000).",
    motivo="Motivo del préstamo.",
    fecha_emision="Fecha de emisión del préstamo.",
    fecha_pago="Fecha límite de pago del préstamo."
)
async def prestamo(interaction: discord.Interaction, 
                   usuario: discord.Member, 
                   labor: str, 
                   monto: int, 
                   motivo: str, 
                   fecha_emision: str, 
                   fecha_pago: str):

    # Verificar que el comando se use solo en el canal autorizado
    if interaction.channel.id != 1390915550921621555:
        return await interaction.response.send_message(
            "❌ Este comando no está permitido en este canal. Por favor úsalo en: https://discord.com/channels/1390915546865729677/1390915550921621555", 
            ephemeral=True
        )

    roles_bloqueados = [1390915547226705998, 1390915547226705997, 1390915547226705996, 
                        1390915547226705995, 1390915547226705994, 1390915547226705993, 
                        1390915547226705992]

    if any(role.id in roles_bloqueados for role in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ Usted no puede realizar un préstamo debido a que es perteneciente a una banda o cuenta con delitos.", 
            ephemeral=True
        )

    if monto > 60000:
        return await interaction.response.send_message("❌ El monto máximo permitido es de 60000.", ephemeral=True)

    nota_adicional = "✅ Préstamo aprobado. Cumple con los requisitos."

    # Guardar en la base de datos
    c.execute('''
        INSERT INTO prestamos (usuario_id, labor, monto, motivo, fecha_emision, fecha_pago, responsable_id, nota_adicional)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (usuario.id, labor, monto, motivo, fecha_emision, fecha_pago, interaction.user.id, nota_adicional))
    conn.commit()

    # Crear embed rojo
    embed = discord.Embed(title="📄 SOLICITUD DE PRÉSTAMO", color=discord.Color.red())
    embed.set_thumbnail(url="https://play-lh.googleusercontent.com/Ma1NGNRR9qTl2N-TFuFFF2Htkk3vVWKmUh9b9C_lyIS6PxWkbKaAEz2o5cACGXI7lgc")
    embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
    embed.add_field(name="🛠️ Labor", value=labor, inline=True)
    embed.add_field(name="💰 Monto", value=f"${monto:,}", inline=True)
    embed.add_field(name="📄 Motivo", value=motivo, inline=False)
    embed.add_field(name="📆 Fecha de emisión", value=fecha_emision, inline=True)
    embed.add_field(name="📆 Fecha de pago", value=fecha_pago, inline=True)
    embed.add_field(name="📌 Nota adicional", value=nota_adicional, inline=False)
    embed.set_footer(text="Derechos reservados de UIO ATAHUALPA RP | ER:LC.",
                     icon_url="https://cdn.discordapp.com/attachments/1397851859036930088/1398786910150983690/IMG_5793.png")

    await interaction.response.send_message(embed=embed)

    # Notificar al rol para que ejecute el comando correspondiente
    canal = interaction.channel
    await canal.send(f"<@&1401073765252730951> aplica el comando correspondiente ya que el préstamo fue aceptado")




#Sincronizar comandos
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")


from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot activo"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def mantener_vivo():
    t = Thread(target=run_web)
    t.start()

mantener_vivo()

bot.run(os.environ["DISCORD_BOT_TOKEN"])