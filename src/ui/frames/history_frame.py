"""
Frame d'historique et rollback.
Interface pour voir l'historique et annuler les opérations.
"""

from tkinter import messagebox
from typing import Callable, Optional

import customtkinter as ctk

from core.operations.file_manager import FileManager
from ui.theme import (
    LABEL_MUTED,
    PAD_M,
    PAD_S,
    danger_button,
    font_label,
    font_mono,
    font_section,
    icon_button,
    warning_button,
)


class HistoryFrame(ctk.CTkFrame):
    """Frame d'historique des opérations."""

    def __init__(
        self,
        parent,
        file_manager: Optional[FileManager] = None,
        status_callback: Optional[Callable] = None
    ):
        """
        Initialise le frame d'historique.

        Args:
            parent: Widget parent
            file_manager: Gestionnaire de fichiers partagé (créé si None).
                Doit obligatoirement être le **même** que celui des autres
                frames pour que l'historique reflète les opérations réelles.
            status_callback: Callback pour la barre de statut
        """
        super().__init__(parent, fg_color="transparent")

        self.status_callback = status_callback or (lambda m, p=None: None)
        self.file_manager = file_manager or FileManager()

        self._create_ui()
        self._refresh_history()

    def _create_ui(self):
        """Refonte UI v3 : 3 zones compactes.

        ┌──────────────────────────────────────────────┐
        │ Titre + stats inline                          │  1 ligne
        ├──────────────────────────────────────────────┤
        │ history_textbox (toute la hauteur)            │  weight=1
        ├──────────────────────────────────────────────┤
        │ [↩️ Dernière] [↩️ Tout]   [🔄] [🗑️ Effacer]    │  1 ligne
        └──────────────────────────────────────────────┘
        """
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # textbox prend toute la hauteur

        # ZONE 1 : titre + stats sur une seule ligne
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_M, PAD_S))
        header.columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header, text="📜 Historique des opérations",
            font=font_section(), anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="w")

        # Stats inline à droite, mises à jour par _refresh_history
        self.stats_label = ctk.CTkLabel(
            header, text="Aucune opération",
            font=font_label(), anchor="e",
            text_color=LABEL_MUTED,
        )
        self.stats_label.grid(row=0, column=1, sticky="e")

        # ZONE 2 : textbox plein écran
        self.history_textbox = ctk.CTkTextbox(
            self, font=font_mono(11),
        )
        self.history_textbox.grid(row=1, column=0, sticky="nsew",
                                  padx=PAD_M, pady=PAD_S)

        # ZONE 3 : boutons sticky bottom
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, PAD_M))
        actions.columnconfigure(2, weight=1)  # spacer entre rollback et clear

        # Gauche : boutons rollback (warning orange = action sérieuse)
        self.rollback_one_button = warning_button(
            actions, text="↩️ Annuler dernière",
            command=self._rollback_last, state="disabled",
        )
        self.rollback_one_button.grid(row=0, column=0, padx=(0, PAD_S), sticky="w")

        self.rollback_all_button = warning_button(
            actions, text="↩️ Annuler tout",
            command=self._rollback_all, state="disabled",
        )
        self.rollback_all_button.grid(row=0, column=1, padx=(0, PAD_S), sticky="w")

        # Droite : refresh (icon) + clear (danger)
        icon_button(actions, text="🔄",
                    command=self._refresh_history).grid(
            row=0, column=3, padx=(0, PAD_S), sticky="e",
        )
        self.clear_button = danger_button(
            actions, text="🗑️ Effacer",
            command=self._clear_history,
        )
        self.clear_button.grid(row=0, column=4, sticky="e")

    def _refresh_history(self):
        """Rafraîchit l'affichage de l'historique."""
        operations = self.file_manager.get_operations_history()

        # Mettre à jour les statistiques
        total = len(operations)
        success = sum(1 for op in operations if op.success)
        errors = total - success

        if total > 0:
            # Format compact pour la zone titre (1 ligne)
            self.stats_label.configure(
                text=f"{total} op. — ✅ {success}  ❌ {errors}"
            )
            self.rollback_one_button.configure(state="normal")
            self.rollback_all_button.configure(state="normal")
        else:
            self.stats_label.configure(text="Aucune opération")
            self.rollback_one_button.configure(state="disabled")
            self.rollback_all_button.configure(state="disabled")

        # Mettre à jour la liste
        self.history_textbox.delete("1.0", "end")

        if not operations:
            self.history_textbox.insert("end", "Aucune opération enregistrée.\n\n")
            self.history_textbox.insert("end", "Les opérations apparaîtront ici après\n")
            self.history_textbox.insert("end", "avoir organisé des fichiers.")
            return

        # Afficher les opérations (les plus récentes en premier)
        for i, op in enumerate(reversed(operations), 1):
            status_icon = "✅" if op.success else "❌"
            op_type = {"copy": "Copié", "move": "Déplacé", "rename": "Renommé", "delete": "Supprimé"}.get(
                op.operation_type, op.operation_type
            )

            self.history_textbox.insert("end", f"\n{'─'*50}\n")
            self.history_textbox.insert("end", f"{status_icon} #{i} - {op_type}\n")
            self.history_textbox.insert("end", f"   De: {op.source}\n")
            self.history_textbox.insert("end", f"   Vers: {op.destination}\n")
            self.history_textbox.insert("end", f"   Heure: {op.timestamp.strftime('%H:%M:%S')}\n")

            if op.error:
                self.history_textbox.insert("end", f"   Erreur: {op.error}\n")

        self.status_callback(f"Historique: {total} opérations")

    def _rollback_last(self):
        """Annule la dernière opération."""
        if not messagebox.askyesno(
            "Confirmation",
            "Voulez-vous annuler la dernière opération?"
        ):
            return

        success = self.file_manager.rollback_last()

        if success:
            messagebox.showinfo("Succès", "La dernière opération a été annulée.")
        else:
            messagebox.showerror("Erreur", "Impossible d'annuler la dernière opération.")

        self._refresh_history()

    def _rollback_all(self):
        """Annule toutes les opérations.

        Affiche un compte-rendu détaillé : succès / échecs / ignorées
        si ``rollback_all`` retourne le dict enrichi.
        """
        operations = self.file_manager.get_operations_history()

        if not operations:
            return

        if not messagebox.askyesno(
            "Confirmation",
            f"Voulez-vous annuler toutes les {len(operations)} opérations?\n\n"
            "Cette action restaurera tous les fichiers à leur emplacement d'origine."
        ):
            return

        result = self.file_manager.rollback_all()

        # Rétro-compatibilité avec l'ancienne API qui renvoyait un int.
        if isinstance(result, int):
            summary = f"{result} opérations ont été annulées."
            messagebox.showinfo("Succès", summary)
        else:
            summary = (
                f"Rollback terminé sur {result.get('total', 0)} opération(s) :\n\n"
                f"  ✅ Annulées : {result.get('success', 0)}\n"
                f"  ❌ Échecs   : {result.get('failed', 0)}\n"
                f"  ∅  Ignorées : {result.get('skipped', 0)}"
            )
            if result.get('failed', 0) > 0:
                messagebox.showwarning("Rollback partiel", summary)
            else:
                messagebox.showinfo("Rollback terminé", summary)

        self._refresh_history()

    def _clear_history(self):
        """Efface l'historique sans annuler."""
        if not messagebox.askyesno(
            "Confirmation",
            "Voulez-vous effacer l'historique?\n\n"
            "Les fichiers ne seront PAS restaurés, seul l'historique sera supprimé."
        ):
            return

        # Effacer via l'API publique (évite l'accès au _privé)
        self.file_manager.clear_history()

        self._refresh_history()
        messagebox.showinfo("Succès", "L'historique a été effacé.")

    def refresh(self):
        """Rafraîchissement public, appelé au changement d'onglet."""
        self._refresh_history()
