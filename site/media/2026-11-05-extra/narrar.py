import asyncio,json
from pathlib import Path
import edge_tts
ROOT=Path(__file__).parent
lines=[
'Diez noticias para cerrar este cinco de noviembre.',
'La República: Nutresa cerró la compra de Presto.',
'También informa: Davivienda incorporó clientes de Davibank.',
'Noticias RCN: el dólar promedió tres mil doscientos veintiocho pesos con diecinueve.',
'La República: una garantía respalda crédito para el Metro de Bogotá.',
'Minciencias propone cooperación con Corea en inteligencia artificial.',
'EFE: Santiago Peña presentó su renuncia en Paraguay.',
'En Israel, EFE informa: Herzog encargará formar Gobierno el domingo.',
'En Ecuador, EFE reporta juicio a José Serrano por el caso Villavicencio. No es una condena.',
'EFE: Zelenski pide equipos para reparar la red eléctrica.',
'EuroEFE: António Costa pide reforzar la cooperación con Latinoamérica.',
'Escucha el desarrollo completo en nuestra web. Toca el enlace del perfil de resumen punto noticias.'
]
(ROOT/'guion.json').write_text(json.dumps(lines,ensure_ascii=False,indent=2))
(ROOT/'guion.txt').write_text('\n'.join(lines))
async def main():
 com=edge_tts.Communicate(' '.join(lines),'es-CO-SalomeNeural',boundary='WordBoundary')
 await com.save(str(ROOT/'voz.mp3'),str(ROOT/'palabras.jsonl'))
 print('Audio generado')
asyncio.run(main())
