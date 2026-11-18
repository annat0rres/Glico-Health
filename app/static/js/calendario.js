document.addEventListener('DOMContentLoaded', function () {
    const calendarEl = document.getElementById('calendario');
    const detailsEl = document.getElementById('detalhes-dia');
    const selectedDateEl = document.getElementById('data-selecionada');
    const entriesEl = document.getElementById('lista-marcacoes');
    const addEntryEl = document.getElementById('adicionar-marcacao');
    const detailsViewEl = document.getElementById('visualizacao-marcacoes');
    const newEntryEl = document.getElementById('novo-registro');
    const newDateEl = document.getElementById('nova-data');
    const cancelEntryEl = document.getElementById('cancelar-registro');
    const cancelDayDetailsEl = document.getElementById('cancelar-dia-marcacao');
    const formTitleEl = document.getElementById('form-titulo');
    const formIconEl = document.getElementById('form-icone');
    const saveEntryEl = document.getElementById('salvar-registro');
    const eventIdEl = document.getElementById('evento-id');
    const typeEl = document.getElementById('novo-tipo');
    const timeEl = document.getElementById('nova-hora');
    const nameEl = document.getElementById('novo-nome');
    const descriptionEl = document.getElementById('nova-descricao');
    const createEventUrl = newEntryEl.dataset.createUrl;
    const editEventUrl = newEntryEl.dataset.editUrl;
    const deleteEventUrl = newEntryEl.dataset.deleteUrl;
    const events = JSON.parse(document.getElementById('eventos-calendario').textContent || '[]');
    const colorsByType = {
        'Consulta médica': '#655A7C',
        'Exame': '#E8B84A',
        'Vacina': '#8ED8E8',
        'Tomar medicação': '#FFBCDC',
        'Outro': '#C49A6C'
    };
    const completedStorageKey = 'glicohealth-marcacoes-concluidas';
    const completedEntries = JSON.parse(localStorage.getItem(completedStorageKey) || '{}');

    events.forEach((event) => {
        event.color = colorsByType[event.tipo] || '#9A8EAA';
        event.textColor = '#ffffff';
        event.completed = Boolean(completedEntries[event.id]);
    });

    const datesWithEvents = new Set(
        events.map((event) => event.start.slice(0, 10))
    );

    const formatDate = (date) => new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(new Date(`${date}T12:00:00`));

    const formatTime = (date) => new Intl.DateTimeFormat('pt-BR', {
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(date));

    function showDayDetails(date) {
        const dayEvents = events.filter((event) => event.start.slice(0, 10) === date);

        selectedDateEl.dataset.date = date;
        selectedDateEl.textContent = formatDate(date);
        entriesEl.innerHTML = dayEvents.length
            ? dayEvents.map((event) => `
                <article class="marcacao-item${event.completed ? ' concluida' : ''}">
                    <button class="marcacao-check" type="button" data-event-id="${event.id}"
                        aria-label="${event.completed ? 'Marcação concluída' : 'Marcar como concluída'}"
                        aria-pressed="${event.completed}">
                        <i class="bi bi-check2" aria-hidden="true"></i>
                    </button>
                    <div>
                        <strong>${event.title}</strong>
                        <span>${formatTime(event.start)}${event.description ? ` · ${event.description}` : ''}</span>
                    </div>
                    <div class="acoes-marcacao">
                        <button class="acao-marcacao editar-marcacao" type="button" data-event-id="${event.id}" aria-label="Editar marcação" title="Editar">
                            <i class="bi bi-pencil" aria-hidden="true"></i>
                        </button>
                        <button class="acao-marcacao excluir-marcacao" type="button" data-event-id="${event.id}" aria-label="Excluir marcação" title="Excluir">
                            <i class="bi bi-trash3" aria-hidden="true"></i>
                        </button>
                    </div>
                </article>
            `).join('')
            : '<p class="sem-marcacoes">Nenhuma marcação para este dia.</p>';

        newDateEl.value = date;
        detailsViewEl.classList.remove('d-none');
        newEntryEl.classList.add('d-none');
        detailsEl.classList.remove('d-none');
    }

    function openForm(eventToEdit = null, selectedDate = '') {
        newEntryEl.reset();
        eventIdEl.value = eventToEdit ? eventToEdit.id : '';
        newDateEl.value = eventToEdit ? eventToEdit.start.slice(0, 10) : selectedDate;
        if (eventToEdit) {
            typeEl.value = eventToEdit.tipo === 'Tomar medicação' ? 'Remédio' : eventToEdit.tipo || 'Outro';
            timeEl.value = eventToEdit.start.slice(11, 16);
            nameEl.value = eventToEdit.title;
            descriptionEl.value = eventToEdit.description;
            newEntryEl.action = editEventUrl.replace('/0', `/${eventToEdit.id}`);
            formTitleEl.textContent = 'Editar marcação';
            formIconEl.className = 'bi bi-pencil-square';
            saveEntryEl.textContent = 'Atualizar';
        } else {
            newEntryEl.action = createEventUrl;
            formTitleEl.textContent = 'Adicionar marcação';
            formIconEl.className = 'bi bi-calendar-plus';
            saveEntryEl.textContent = 'Salvar';
        }
        detailsViewEl.classList.add('d-none');
        newEntryEl.classList.remove('d-none');
    }

    function showDeleteConfirmation(selectedEvent) {
        const popup = document.createElement('div');
        popup.className = 'popup-confirmacao';
        popup.innerHTML = `
            <div class="popup-confirmacao-conteudo" role="dialog" aria-modal="true" aria-labelledby="popup-titulo">
                <div class="popup-confirmacao-icone"><i class="bi bi-trash3" aria-hidden="true"></i></div>
                <h2 id="popup-titulo">Excluir marcação?</h2>
                <p>Essa ação não poderá ser desfeita.</p>
                <div class="popup-confirmacao-acoes">
                    <button class="popup-cancelar" type="button">Cancelar</button>
                    <button class="popup-confirmar" type="button">Excluir</button>
                </div>
            </div>
        `;

        const closePopup = () => popup.remove();
        popup.addEventListener('click', (event) => {
            if (event.target === popup) closePopup();
        });
        popup.querySelector('.popup-cancelar').addEventListener('click', closePopup);
        popup.querySelector('.popup-confirmar').addEventListener('click', () => {
            const deleteForm = document.createElement('form');
            const deleteUrl = deleteEventUrl.replace('/0', `/${selectedEvent.id}`);
            const csrfToken = newEntryEl.querySelector('[name="csrf_token"]').value;

            deleteForm.method = 'POST';
            deleteForm.action = deleteUrl;
            deleteForm.innerHTML = `<input type="hidden" name="csrf_token" value="${csrfToken}">`;
            document.body.appendChild(deleteForm);
            deleteForm.submit();
        });
        document.body.appendChild(popup);
        popup.querySelector('.popup-cancelar').focus();
    }

    entriesEl.addEventListener('click', (event) => {
        const checkButton = event.target.closest('.marcacao-check');
        const editButton = event.target.closest('.editar-marcacao');
        const deleteButton = event.target.closest('.excluir-marcacao');
        const clickedButton = checkButton || editButton || deleteButton;
        if (!clickedButton) return;

        const selectedEvent = events.find((entry) => String(entry.id) === clickedButton.dataset.eventId);
        if (!selectedEvent) return;

        if (editButton) {
            openForm(selectedEvent);
            return;
        }

        if (deleteButton) {
            showDeleteConfirmation(selectedEvent);
            return;
        }

        selectedEvent.completed = !selectedEvent.completed;
        if (selectedEvent.completed) {
            completedEntries[selectedEvent.id] = true;
        } else {
            delete completedEntries[selectedEvent.id];
        }
        localStorage.setItem(completedStorageKey, JSON.stringify(completedEntries));
        showDayDetails(selectedEvent.start.slice(0, 10));
    });

    addEntryEl.addEventListener('click', () => {
        openForm(null, selectedDateEl.dataset.date || newDateEl.value);
    });

    cancelEntryEl.addEventListener('click', () => {
        newEntryEl.reset();
        newEntryEl.classList.add('d-none');
        detailsViewEl.classList.remove('d-none');
    });

    cancelDayDetailsEl.addEventListener('click', () => {
        detailsEl.classList.add('d-none');
        newEntryEl.classList.add('d-none');
        detailsViewEl.classList.remove('d-none');
    });

    const calendar = new FullCalendar.Calendar(calendarEl, {
        themeSystem: 'monarch', 
        initialView: 'dayGridMonth',
        locale: 'pt-br', 
        headerToolbar: {
            left: 'prev',
            center: 'title',
            right: 'next'
        },
        height: 'auto',
        fixedWeekCount: false,
        handleWindowResize: true,
        events,
        dayCellClassNames: (info) => {
            const year = info.date.getFullYear();
            const month = String(info.date.getMonth() + 1).padStart(2, '0');
            const day = String(info.date.getDate()).padStart(2, '0');
            const dateKey = `${year}-${month}-${day}`;

            return datesWithEvents.has(dateKey) ? ['dia-com-marcacao'] : [];
        },
        dateClick: (info) => showDayDetails(info.dateStr),
        eventClick: (info) => showDayDetails(info.event.startStr.slice(0, 10))
    });

    calendar.render();
});