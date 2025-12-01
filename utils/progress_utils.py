# utils/progress_utils.py
"""Utilitaires pour la gestion de la progression."""

import threading

class ProgressManager:
    """
    Gestionnaire de progression pour les tâches de longue durée.
    """
    def __init__(self, progress_bar, status_var, max_value=100):
        """
        Initialise le gestionnaire de progression.
        
        Args:
            progress_bar (ttk.Progressbar): Barre de progression Tkinter
            status_var (tk.StringVar): Variable pour le message de statut
            max_value (int): Valeur maximale de la progression
        """
        self.progress_bar = progress_bar
        self.status_var = status_var
        self.max_value = max_value
    
    def update(self, value, message=None):
        """
        Met à jour la progression.

        Args:
            value (int): Valeur actuelle
            message (str): Message de statut à afficher
        """
        progress = (value / self.max_value) * 100
        self.progress_bar["value"] = progress

        if message:
            self.status_var.set(message)
        else:
            self.status_var.set(f"Progression: {value}/{self.max_value}")

    def reset(self):
        """Réinitialise la barre de progression à zéro."""
        self.progress_bar["value"] = 0
        self.status_var.set("Prêt")

class ThreadedTask:
    """
    Classe pour exécuter une tâche dans un thread séparé avec un gestionnaire de progression.
    """
    def __init__(self, task_func, progress_manager, on_complete=None):
        """
        Initialise la tâche threadée.
        
        Args:
            task_func (callable): Fonction à exécuter
            progress_manager (ProgressManager): Gestionnaire de progression
            on_complete (callable): Fonction à appeler lorsque la tâche est terminée
        """
        self.task_func = task_func
        self.progress_manager = progress_manager
        self.on_complete = on_complete
        self.result = None
        self.thread = None
        self.cancelled = False
    
    def _thread_func(self):
        """Fonction exécutée dans le thread."""
        try:
            if not self.cancelled:
                self.result = self.task_func(self.progress_manager)

            # Appeler la fonction de rappel dans le thread principal
            if self.on_complete:
                # Utiliser after pour exécuter la fonction dans le thread principal
                self.progress_manager.progress_bar.after(10, lambda: self.on_complete(self.result))

        except Exception as e:
            print(f"Erreur dans la tâche threadée: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """Démarre la tâche dans un thread séparé."""
        self.thread = threading.Thread(target=self._thread_func, daemon=True)
        self.thread.start()
    
    def is_running(self):
        """
        Vérifie si la tâche est en cours d'exécution.
        
        Returns:
            bool: True si la tâche est en cours d'exécution, False sinon
        """
        return self.thread is not None and self.thread.is_alive()
        
    def cancel(self):
        """
        Annule la tâche en cours d'exécution.
        """
        self.cancelled = True