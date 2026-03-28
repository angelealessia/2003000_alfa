// Configurazione simulazione
const IS_MOCK_MODE = true; 

// 1. Gestione Orologio UTC (Top Right)
setInterval(() => {
    const now = new Date();
    document.getElementById('clock').innerText = now.toISOString().split('T')[1].split('.')[0] + " UTC";
}, 1000);

// 2. Funzione di Rendering (La parte "Bella")
function renderEvent(data) {
    const container = document.getElementById('alerts-container');
    const historyTable = document.getElementById('history-table');
    const { sensor_id, timestamp, value, frequency } = data;
    
    // Configurazione stili in base alla frequenza
    let config = {
        label: "SEISMIC ACTIVITY",
        color: "text-emerald-400",
        border: "border-emerald-500/30",
        bg: "bg-emerald-500/5",
        icon: "◍"
    };

    if (frequency >= 8.0) {
        config = { 
            label: "⚠️ NUCLEAR EVENT DETECTED", 
            color: "text-red-500", 
            border: "border-red-600", 
            bg: "bg-red-950/40", 
            extra: "nuclear-alert",
            icon: "☢"
        };
        // Trigger allarme globale
        document.getElementById('threat-level').innerText = "CRITICAL";
        document.getElementById('threat-level').className = "text-2xl font-bold text-red-600 animate-pulse";
    } else if (frequency >= 3.0) {
        config = { 
            label: "CONVENTIONAL EXPLOSION", 
            color: "text-amber-500", 
            border: "border-amber-700/50", 
            bg: "bg-amber-900/20",
            icon: "▲"
        };
    }

    // Aggiunta al Feed Live (con animazione d'entrata)
    const eventHtml = `
        <div class="p-4 border-l-4 ${config.border} ${config.bg} ${config.extra || ''} transform transition-all duration-500 translate-x-0 opacity-100">
            <div class="flex justify-between items-start mb-1">
                <span class="text-[10px] font-black ${config.color} tracking-[0.2em] uppercase">
                    ${config.icon} ${config.label}
                </span>
                <span class="text-[9px] text-slate-500 font-mono">${new Date(timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="flex justify-between items-end">
                <div>
                    <span class="text-xs text-slate-500 block uppercase text-[9px]">Origin Source</span>
                    <span class="text-sm font-bold text-slate-200">${sensor_id}</span>
                </div>
                <div class="text-right">
                    <span class="text-xs text-slate-500 block uppercase text-[9px]">Magnitude</span>
                    <span class="text-lg font-black ${config.color}">${frequency.toFixed(2)} <span class="text-[10px]">Hz</span></span>
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('afterbegin', eventHtml);

    // Limitiamo i messaggi nel feed per non rallentare il browser
    if (container.children.length > 50) container.lastElementChild.remove();

    // Aggiunta allo storico (tabella)
    const rowHtml = `
        <tr class="border-b border-slate-800/30 hover:bg-slate-800/20 transition-colors">
            <td class="py-2 text-slate-500">${new Date(timestamp).toLocaleTimeString()}</td>
            <td class="font-bold text-cyan-700">${sensor_id}</td>
            <td class="text-right font-bold ${config.color}">${config.label.split(' ')[0]}</td>
        </tr>
    `;
    historyTable.insertAdjacentHTML('afterbegin', rowHtml);
}

// 3. Generatore di Dati Fake (Solo per test)
if (IS_MOCK_MODE) {
    console.warn("DASHBOARD IN MOCK MODE: Generating random seismic data...");
    document.getElementById('sensor-count').innerText = "12";
    
    setInterval(() => {
        const rand = Math.random() * 10;
        const mockData = {
            sensor_id: "SNSR-" + Math.floor(Math.random() * 999).toString().padStart(3, '0'),
            timestamp: new Date().toISOString(),
            value: (Math.random() * 50).toFixed(2),
            frequency: rand
        };
        renderEvent(mockData);
    }, 3000); // Genera un evento ogni 3 secondi
}