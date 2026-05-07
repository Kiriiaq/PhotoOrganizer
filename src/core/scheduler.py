# -*- coding: utf-8 -*-
"""
Module de planification des organisations (Lot E5).

Permet de programmer une exécution quotidienne automatique de l'organisation
(par exemple « tous les jours à 23:00 ») tant que l'application est ouverte.

Volontairement sans dépendance externe : on fait tourner un thread daemon
qui calcule le prochain trigger HH:MM et appelle un callback à l'heure
voulue. Si l'app est fermée au moment du trigger, l'exécution est sautée
(pas de tâche planifiée Windows native — c'est un scheduler in-app).

Persistance dans ``AppConfig.schedule_*`` :
    - schedule_enabled     (bool)
    - schedule_time        ("HH:MM")
    - schedule_source      (chemin source ou plusieurs séparés par ;)
    - schedule_destination (chemin destination)
    - schedule_preset      (nom du preset à appliquer, ou "" pour défauts)
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class JobScheduler:
    """Scheduler in-app, à thread unique, granularité 1 minute.

    Le thread se réveille toutes les ``poll_seconds`` (60 par défaut) pour
    comparer l'heure courante au ``HH:MM`` configuré. Quand l'heure est
    atteinte (avec une fenêtre de tolérance ≤ 1 minute), il invoque le
    callback et marque le run comme "fait pour aujourd'hui" pour éviter de
    le déclencher plusieurs fois à la même minute.
    """

    def __init__(
        self,
        callback: Callable[[], None],
        poll_seconds: int = 60,
    ):
        """
        Args:
            callback: Fonction à appeler quand l'heure planifiée est atteinte.
                Doit être thread-safe (déléguer le travail UI via .after()).
            poll_seconds: Période de réveil du thread (défaut 60 s).
        """
        self._callback = callback
        self._poll_seconds = max(5, poll_seconds)

        self._enabled = False
        self._scheduled_time: Optional[str] = None  # "HH:MM"
        self._last_run_date: Optional[datetime.date] = None  # type: ignore[name-defined]

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # ----------------------------------------------------------------
    # Configuration
    # ----------------------------------------------------------------
    def configure(self, enabled: bool, scheduled_time: Optional[str]):
        """Active/désactive et fixe l'heure planifiée (format ``"HH:MM"``).

        Si désactivé, le thread est arrêté. Si activé et que l'heure est
        valide, le thread est (re)démarré.
        """
        with self._lock:
            self._enabled = enabled
            self._scheduled_time = self._normalize_time(scheduled_time)
            # Reset du marqueur du dernier run pour autoriser un nouveau
            # déclenchement aujourd'hui si l'utilisateur change l'heure.
            self._last_run_date = None

        if enabled and self._scheduled_time:
            self.start()
        else:
            self.stop()

    @staticmethod
    def _normalize_time(value: Optional[str]) -> Optional[str]:
        """Normalise/valide une heure HH:MM. Retourne None si invalide."""
        if not value:
            return None
        try:
            h, m = value.split(':')
            hh = int(h)
            mm = int(m)
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                return f"{hh:02d}:{mm:02d}"
        except (ValueError, AttributeError):
            pass
        return None

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------
    def start(self):
        """Démarre le thread daemon (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="JobScheduler"
        )
        self._thread.start()
        logger.info(
            f"Scheduler demarre (heure planifiee : {self._scheduled_time})"
        )

    def stop(self):
        """Stoppe proprement le thread (idempotent)."""
        self._stop_event.set()
        if self._thread is not None:
            # On ne join pas avec timeout long pour ne pas bloquer la
            # fermeture UI : daemon=True garantit le clean au shutdown.
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.debug("Scheduler arrete")

    # ----------------------------------------------------------------
    # Boucle interne
    # ----------------------------------------------------------------
    def _run(self):
        while not self._stop_event.is_set():
            with self._lock:
                enabled = self._enabled
                scheduled = self._scheduled_time
                last = self._last_run_date

            if enabled and scheduled:
                now = datetime.now()
                hh, mm = scheduled.split(':')
                if (
                    now.hour == int(hh)
                    and now.minute == int(mm)
                    and last != now.date()
                ):
                    logger.info(f"Scheduler trigger : {scheduled}")
                    try:
                        self._callback()
                    except Exception as exc:
                        logger.error(f"Callback scheduler en erreur : {exc}")
                    with self._lock:
                        self._last_run_date = now.date()

            # Sleep avec event pour pouvoir réveiller au stop()
            self._stop_event.wait(timeout=self._poll_seconds)

    # ----------------------------------------------------------------
    # Introspection (pour l'UI)
    # ----------------------------------------------------------------
    def get_next_run(self) -> Optional[datetime]:
        """Retourne le prochain trigger calculé, ou None si désactivé."""
        with self._lock:
            if not self._enabled or not self._scheduled_time:
                return None
            scheduled = self._scheduled_time
            last = self._last_run_date

        hh, mm = scheduled.split(':')
        now = datetime.now()
        candidate = now.replace(
            hour=int(hh), minute=int(mm), second=0, microsecond=0
        )
        if candidate <= now or last == now.date():
            candidate += timedelta(days=1)
        return candidate

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled and self._scheduled_time is not None
