"""
Frame d'historique et rollback.
Interface pour voir l'historique et annuler les opérations.
"""

import os
from typing import Optional, Callable
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox

from core.operations.file_manager import FileManager, FileOperation


class HistoryFrame(ctk.CTkFrame):
    """Frame d'historique des opérations."""

    def __init__(
        self,
        parent,
        status_callback: Optional[Callable] = None
    ):
        """
        Initialise le frame d'historique.

        Args:
            parent: Widget parent
            status_callback: Callback pour la barre de statut
        """
        super().__init__(parent, fg_color="transparent")

        self.status_callback = status_callback or (lambda m, p=None: None)
        self.file_manager = FileManager()

        self._create_ui()

    def _create_ui(self):
        """Crée l'interface utilisateur."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # En-tête
        self._create_header()

        # Liste des opérations
        self._create_operations_list()

        # Actions
        self._create_actions_section()

    def _create_header(self):
        """Crée l'en-tête."""
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(
            header_frame,
            text="📜 Historique des opérations",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=10)

        info_label = ctk.CTkLabel(
            header_frame,
            text="Les opérations de la session actuelle sont listées ci-dessous.\n"
                 "Vous pouvez annuler les opérations en sens inverse.",
            justify="left"
        )
        info_label.pack(anchor="w", padx=10, pady=(0, 10))

    def _create_operations_list(self):
        """Crée la liste des opérations."""
        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Statistiques
        self.stats_label = ctk.CTkLabel(
            list_frame,
            text="Aucune opération dans cette session.",
            font=ctk.CTkFont(size=12)
        )
        self.stats_label.pack(anchor="w", padx=10, pady=10)

        # Zone de texte pour l'historique
        self.history_textbox = ctk.CTkTextbox(list_frame, height=300)
        self.history_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Bouton de rafraîchissement
        ctk.CTkButton(
            list_frame,
            text="🔄 Rafraîchir",
            command=self._refresh_history
        ).pack(pady=10)

    def _create_actions_section(self):
        """Crée la section des actions."""
        actions_frame = ctk.CTkFrame(self)
        actions_frame.grid(row=2, column=0, sticky="sew", padx=10, pady=10)

        # Avertissement
        warning_label = ctk.CTkLabel(
            actions_frame,
            text="⚠️ L'annulation (rollback) restaure les fichiers à leur emplacement d'origine.",
            text_color="orange"
        )
        warning_label.pack(padx=10, pady=10)

        # Boutons
        buttons_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=10, pady=10)

        self.rollback_one_button = ctk.CTkButton(
            buttons_frame,
            text="↩️ Annuler dernière",
            command=self._rollback_last,
            state="disabled"
        )
        self.rollback_one_button.pack(side="left", padx=5, expand=True, fill="x")

        self.rollback_all_button = ctk.CTkButton(
            buttons_frame,
            text="↩️ Annuler tout",
            command=self._rollback_all,
            state="disabled",
            fg_color="orange",
            hover_color="darkorange"
        )
        self.rollback_all_button.pack(side="left", padx=5, expand=True, fill="x")

        self.clear_button = ctk.CTkButton(
            buttons_frame,
            text="🗑️ Effacer historique",
            command=self._clear_history,
            fg_color="red",
            hover_color="darkred"
        )
        self.clear_button.pack(side="left", padx=5, expand=True, fill="x")

    def _refresh_history(self):
        """Rafraîchit l'affichage de l'historique."""
        operations = self.file_manager.get_operations_history()

        # Mettre à jour les statistiques
        total = len(operations)
        success = sum(1 for op in operations if op.success)
        errors = total - success

        if total > 0:
            self.stats_label.configure(
                text=f"Session actuelle: {total} opérations ({success} réussies, {errors} erreurs)"
            )
            self.rollback_one_button.configure(state="normal")
            self.rollback_all_button.configure(state="normal")
        else:
            self.stats_label.configure(text="Aucune opération dans cette session.")
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
        """Annule toutes les opérations."""
        operations = self.file_manager.get_operations_history()

        if not operations:
            return

        if not messagebox.askyesno(
            "Confirmation",
            f"Voulez-vous annuler toutes les {len(operations)} opérations?\n\n"
            "Cette action restaurera tous les fichiers à leur emplacement d'origine."
        ):
            return

        count = self.file_manager.rollback_all()

        messagebox.showinfo("Succès", f"{count} opérations ont été annulées.")
        self._refresh_history()

    def _clear_history(self):
        """Efface l'historique sans annuler."""
        if not messagebox.askyesno(
            "Confirmation",
            "Voulez-vous effacer l'historique?\n\n"
            "Les fichiers ne seront PAS restaurés, seul l'historique sera supprimé."
        ):
            return

        # Réinitialiser le gestionnaire
        self.file_manager._operations_history.clear()

        self._refresh_history()
        messagebox.showinfo("Succès", "L'historique a été effacé.")
