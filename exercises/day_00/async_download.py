
import asyncio

async def download_file(name, duration):
    # TODO: afficher le début du téléchargement
    print(f"Downloading {name}...")
    # TODO: attendre sans bloquer
    await asyncio.sleep(duration)
    # TODO: afficher la fin
    print(f"{name} completed")
    # TODO: retourner le nom
    return name

    pass

async def main():
    # TODO: lancer les trois téléchargements
    # de manière concurrente
    results = await asyncio.gather(
        download_file("files-a", 4),
        download_file("files-b", 7),
        download_file("files-c", 1)
    )

    # TODO: afficher les résultats
    print("Results:", results)
    pass

if __name__ == "__main__":
    # TODO: lancer main() avec asyncio
    asyncio.run(main())
    pass