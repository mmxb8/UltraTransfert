"""Dons volontaires : aucune transaction ni requête réseau automatique."""
import hashlib
from pathlib import Path

BITCOIN_ADDRESS = '3HaGinyFJQJXFAMgU8SBuDxdS5aG5BQUNU'
BITCOIN_URI = 'bitcoin:' + BITCOIN_ADDRESS
QR_PATH = Path(__file__).resolve().parent / 'assets' / 'bitcoin-donation.png'


def valid_bitcoin_address(address):
    """Contrôle Base58Check d'une adresse Bitcoin mainnet P2SH, pas sa propriété."""
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    try:
        if not isinstance(address, str) or not 26 <= len(address) <= 35:
            return False
        value = 0
        for char in address:
            value = value * 58 + alphabet.index(char)
        raw = value.to_bytes((value.bit_length() + 7) // 8, 'big')
        raw = b'\x00' * (len(address) - len(address.lstrip('1'))) + raw
        checksum = hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4]
        return len(raw) == 25 and raw[0] == 5 and checksum == raw[-4:]
    except (ValueError, OverflowError):
        return False


def show_donations(parent):
    import tkinter as tk
    from tkinter import ttk
    if not valid_bitcoin_address(BITCOIN_ADDRESS):
        raise ValueError('Adresse de don Bitcoin invalide.')
    window = tk.Toplevel(parent)
    window.title('Soutenir UltraTransfert')
    window.resizable(False, False)
    panel = ttk.Frame(window, padding=20)
    panel.pack(fill='both', expand=True)
    ttk.Label(panel, text='Soutenir UltraTransfert', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
    ttk.Label(panel, text='Logiciel libre sous licence MIT. Les dons sont facultatifs.\nToutes les fonctions restent disponibles sans don.',
              wraplength=420).pack(anchor='w', pady=(8, 12))
    image = tk.PhotoImage(master=window, file=str(QR_PATH))
    window.donation_qr = image
    ttk.Label(panel, image=image).pack(pady=4)
    ttk.Label(panel, text='Bitcoin (BTC) · réseau Bitcoin uniquement').pack(pady=(8, 4))
    address = ttk.Entry(panel, width=42, justify='center')
    address.insert(0, BITCOIN_ADDRESS)
    address.configure(state='readonly')
    address.pack(fill='x', pady=4)
    status = tk.StringVar(master=window, value='Vérifiez cette adresse dans votre portefeuille avant tout envoi.')

    def copy_address():
        window.clipboard_clear()
        window.clipboard_append(BITCOIN_ADDRESS)
        status.set("Adresse copiée. Aucun paiement n'a été effectué par UltraTransfert.")

    ttk.Button(panel, text="Copier l'adresse Bitcoin", command=copy_address).pack(pady=8)
    ttk.Label(panel, textvariable=status, wraplength=420).pack(anchor='w', pady=4)
    ttk.Button(panel, text='Fermer', command=window.destroy).pack(anchor='e', pady=(10, 0))
    window.bind('<Escape>', lambda event: window.destroy())
    window.transient(parent)
    address.focus_set()
    return window
