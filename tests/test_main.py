import typer

app = typer.Typer()

@app.command()
def main():
    """
    Manage bookings via WhatsApp and calls.
    """
    print("HMS Agent: A multi-agent hotel management system")

if __name__ == "__main__":
    app()