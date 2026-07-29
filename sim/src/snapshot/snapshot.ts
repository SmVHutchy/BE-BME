/**
 * Zustandssicherung.
 *
 * Kernanforderung, kein Komfortmerkmal: Bei einem System, dessen ganzer Sinn
 * die Geschichte ist, darf ein Absturz keine Wochen Verlauf vernichten
 * (Exposé 7.4).
 *
 * Gespeichert wird im Browser ueber IndexedDB. Der Grund ist die Zielumgebung:
 * `sim` laeuft im Kioskmodus in Chromium und hat keinen Dateisystemzugriff. Ein
 * Umweg ueber `core` waere moeglich, wuerde aber 4 MB je Feld ueber den
 * WebSocket schieben und den Vertrag um eine Nachricht erweitern, die nichts
 * mit der Kopplung zu tun hat.
 *
 * Jeder Snapshot traegt Seed, Tick und den Konfigurationshash. Ein Snapshot,
 * der zu einer anderen Konfiguration gehoert, wird nicht wiederhergestellt -
 * sonst liefe die Welt mit Feldern weiter, die unter anderen Parametern
 * entstanden sind, und die Massenbilanz waere von Anfang an unerklaerbar.
 */

const DB_NAME = "frame-sim";
const STORE = "snapshots";
const DB_VERSION = 1;

export interface Snapshot {
  tick: number;
  worldTime: number;
  seed: number;
  configHash: string;
  savedAt: string;
  width: number;
  height: number;
  state: Float32Array;
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "tick" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error(`IndexedDB: ${request.error?.message}`));
  });
}

export async function saveSnapshot(snapshot: Snapshot, keepLast: number): Promise<void> {
  const db = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE, "readwrite");
    transaction.objectStore(STORE).put(snapshot);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(new Error(`Snapshot nicht gespeichert: ${transaction.error?.message}`));
  });

  // Rollierend aufraeumen. Ohne das waechst die Datenbank bei 4 MB je Snapshot
  // und einem Snapshot alle 15 Minuten um rund 380 MB je Tag.
  const keys = await new Promise<IDBValidKey[]>((resolve, reject) => {
    const transaction = db.transaction(STORE, "readonly");
    const request = transaction.objectStore(STORE).getAllKeys();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error("Snapshot-Schluessel nicht lesbar"));
  });

  const obsolete = keys.sort((a, b) => Number(a) - Number(b)).slice(0, -keepLast);
  if (obsolete.length > 0) {
    await new Promise<void>((resolve) => {
      const transaction = db.transaction(STORE, "readwrite");
      const store = transaction.objectStore(STORE);
      for (const key of obsolete) store.delete(key);
      transaction.oncomplete = () => resolve();
    });
  }
  db.close();
}

/**
 * Laedt den juengsten passenden Snapshot.
 *
 * Passend heisst: gleicher Seed, gleicher Konfigurationshash und gleiche
 * Feldgroesse. Alles andere wird uebergangen und der Grund protokolliert -
 * stillschweigend einen unpassenden Zustand zu laden waere schlimmer als ein
 * Neustart bei Tick null.
 */
export async function loadLatestSnapshot(
  seed: number,
  configHash: string,
  width: number,
  height: number,
): Promise<Snapshot | null> {
  const db = await openDatabase();
  const all = await new Promise<Snapshot[]>((resolve, reject) => {
    const transaction = db.transaction(STORE, "readonly");
    const request = transaction.objectStore(STORE).getAll();
    request.onsuccess = () => resolve(request.result as Snapshot[]);
    request.onerror = () => reject(new Error("Snapshots nicht lesbar"));
  });
  db.close();

  const candidates = all.filter((snapshot) => {
    if (snapshot.seed !== seed) return false;
    if (snapshot.width !== width || snapshot.height !== height) return false;
    if (snapshot.configHash !== configHash) {
      console.warn(
        `Snapshot bei Tick ${snapshot.tick} uebergangen: anderer Konfigurationshash ` +
          `(${snapshot.configHash.slice(0, 12)} statt ${configHash.slice(0, 12)}).`,
      );
      return false;
    }
    return true;
  });

  if (candidates.length === 0) return null;
  return candidates.reduce((latest, snapshot) => (snapshot.tick > latest.tick ? snapshot : latest));
}

export async function clearSnapshots(): Promise<void> {
  const db = await openDatabase();
  await new Promise<void>((resolve) => {
    const transaction = db.transaction(STORE, "readwrite");
    transaction.objectStore(STORE).clear();
    transaction.oncomplete = () => resolve();
  });
  db.close();
}
