/*  asistente_finanzas.pl
    SWI-Prolog (7.x/8.x/9.x)
    Módulo de recomendaciones financieras basadas en reglas.
    Fuente de reglas: proyecto del usuario (30+ reglas) con afinaciones prácticas.
*/

:- module(asistente_finanzas, [
    recomendaciones/2,          % +PerfilDict, -ListaDeRecs
    ejemplo_perfil/1            % -PerfilDict
]).

/* =========================
   Representación del Perfil
   =========================
   Usamos un dict SWI-Prolog para claridad:

   Perfil = _{
     ingreso: number,
     gasto_total: number,
     ahorro_mensual: number,
     meses_fondo: number,
     vivienda: number,
     alimentacion: number,
     transporte: number,
     deudas_total: number,
     cc_pago_minimo: boolean,
     tasa_interes_apr: number,
     metas: list(meta(Tipo,PlazoMeses)),
     jubilacion_definida: boolean,
     nivel_conocimiento: basic|intermediate|advanced,
     tiene_seguro_salud: boolean,
     tiene_seguro_vida: boolean,
     dependientes: boolean,
     posee_auto: boolean,
     tiene_seguro_auto: boolean,
     gasto_medico_ratio: number,
     tiene_testamento: boolean,
     registra_gastos: boolean
   }.
*/

%% --------- Utilidades numéricas ---------
safe_div(Num, Den, R) :-
    ( Den =:= 0 -> R = 0 ; R is Num / Den ).

porcentaje(Parte, Todo, Pct) :-
    safe_div(Parte, Todo, R),
    Pct is R * 100.

betweenf(Low, High, X) :- X >= Low, X =< High.

%% --------- Derivados del perfil ---------
tasa_ahorro(Perfil, TasaPct) :-
    I = Perfil.ingreso,
    A = Perfil.ahorro_mensual,
    porcentaje(A, I, TasaPct).

ratio(Parte, Total, R) :- safe_div(Parte, Total, R).
ratio_pct(Parte, Total, Rpct) :- ratio(Parte, Total, R), Rpct is R*100.

ratio_vivienda_pct(Perfil, P) :- ratio_pct(Perfil.vivienda, Perfil.ingreso, P).
ratio_alimentacion_pct(Perfil, P) :- ratio_pct(Perfil.alimentacion, Perfil.ingreso, P).
ratio_transporte_pct(Perfil, P) :- ratio_pct(Perfil.transporte, Perfil.ingreso, P).
ratio_deuda_pct(Perfil, P) :- ratio_pct(Perfil.deudas_total, Perfil.ingreso, P).

gastos_superan_ingresos(Perfil) :- Perfil.gasto_total > Perfil.ingreso.

%% Clasificación de metas por plazo (meses)
plazo_tipo(Meses, corto)    :- Meses < 12, !.
plazo_tipo(Meses, mediano)  :- Meses >= 12, Meses =< 60, !.
plazo_tipo(_, largo).

%% --------- Motor de reglas: recommend/2 ---------
% recommend(+Perfil, -RecomendacionAtom)

% --- Ahorro y fondo de emergencia ---
recommend(Perfil, 'Aumenta tu tasa de ahorro al menos al 10% del ingreso neto.') :-
    tasa_ahorro(Perfil, T), T < 10.

recommend(Perfil, 'Excelente tasa de ahorro (>20%). Considera diversificar una parte en instrumentos de bajo riesgo.') :-
    tasa_ahorro(Perfil, T), T > 20.

recommend(Perfil, 'Crea un fondo de emergencia de 3 a 6 meses de gastos.') :-
    Perfil.meses_fondo =< 0.

recommend(Perfil, 'Incrementa tu fondo de emergencia a al menos 3 meses de gastos.') :-
    Perfil.meses_fondo > 0, Perfil.meses_fondo < 3.

recommend(Perfil, 'Tu fondo ya cubre ~3-6 meses. Evalúa mover el excedente a inversión de bajo riesgo.') :-
    Perfil.meses_fondo >= 6.

% --- Presupuesto ---
recommend(Perfil, 'Tus gastos superan tus ingresos. Recorta de inmediato gastos discrecionales y ajusta el presupuesto.') :-
    gastos_superan_ingresos(Perfil).

recommend(Perfil, 'Gasto en vivienda alto (>40%). Negocia renta/hipoteca o reubica para acercarte al 30% del ingreso.') :-
    ratio_vivienda_pct(Perfil, P), P > 40.

recommend(Perfil, 'Ajusta el gasto en vivienda a ~30% del ingreso; actualmente estás entre 30% y 40%.') :-
    ratio_vivienda_pct(Perfil, P), betweenf(30, 40, P).

recommend(Perfil, 'Gasto en alimentación elevado (>35%). Optimiza compras y planifica menús.') :-
    ratio_alimentacion_pct(Perfil, P), P > 35.

recommend(Perfil, 'Gasto en transporte alto (>20%). Considera alternativas más económicas o rutas compartidas.') :-
    ratio_transporte_pct(Perfil, P), P > 20.

recommend(Perfil, 'Empieza a registrar gastos con un planificador mensual para mejorar control y seguimiento.') :-
    \+ Perfil.registra_gastos.

% --- Deudas ---
recommend(Perfil, 'Sobreendeudamiento: pagos de deuda >=40% del ingreso. Construye un plan agresivo de reducción.') :-
    ratio_deuda_pct(Perfil, P), P >= 40.

recommend(Perfil, 'Evita pagar solo el mínimo en la tarjeta; aumenta el pago mensual para reducir intereses.') :-
    Perfil.cc_pago_minimo == true.

recommend(Perfil, 'APR alta (>30%). Explora consolidación o refinanciamiento para bajar intereses.') :-
    Perfil.tasa_interes_apr > 30.

recommend(Perfil, 'Sin deudas. Mantén buen historial usando crédito responsablemente (bajo uso, pagos completos).') :-
    Perfil.deudas_total =:= 0.

% --- Metas financieras ---
recommend(Perfil, 'Define al menos una meta de ahorro SMART (específica, medible, alcanzable, relevante, temporal).') :-
    ( var(Perfil.metas) ; Perfil.metas == [] ).

recommend(Perfil, 'Meta a corto plazo: prioriza liquidez (cuentas de ahorro de fácil acceso).') :-
    member(meta(_, Meses), Perfil.metas),
    plazo_tipo(Meses, corto).

recommend(Perfil, 'Meta a mediano plazo: usa instrumentos de bajo riesgo y horizontes 1–5 años.') :-
    member(meta(_, Meses), Perfil.metas),
    plazo_tipo(Meses, mediano).

recommend(Perfil, 'Meta a largo plazo: diversifica el portafolio gradualmente.') :-
    member(meta(_, Meses), Perfil.metas),
    plazo_tipo(Meses, largo).

recommend(Perfil, 'Calcula y define tu aporte mensual para jubilación (no lo tienes definido).') :-
    Perfil.jubilacion_definida == false.

% --- Educación y conocimiento financiero ---
recommend(Perfil, 'Nivel básico: toma un curso introductorio y ejercicios prácticos de presupuesto.') :-
    Perfil.nivel_conocimiento == basic.

recommend(Perfil, 'Nivel intermedio: practica con simuladores de inversión y seguimiento de metas.') :-
    Perfil.nivel_conocimiento == intermediate.

recommend(Perfil, 'Nivel avanzado: diversifica más tu portafolio y evalúa rebalanceos periódicos.') :-
    Perfil.nivel_conocimiento == advanced.

% --- Seguros y protección ---
recommend(Perfil, 'No cuentas con seguro de salud: evalúa adquirir un plan básico cuanto antes.') :-
    Perfil.tiene_seguro_salud == false.

recommend(Perfil, 'Con dependientes y sin seguro de vida: considera contratar cobertura de vida.') :-
    Perfil.dependientes == true, Perfil.tiene_seguro_vida == false.

recommend(Perfil, 'Posees auto sin seguro: contrata por obligación legal y protección financiera.') :-
    Perfil.posee_auto == true, Perfil.tiene_seguro_auto == false.

recommend(Perfil, 'Gasto médico >15% del ingreso: un seguro de salud puede reducir volatilidad y riesgo.') :-
    Perfil.gasto_medico_ratio > 0.15.

recommend(Perfil, 'No tienes testamento: busca asesoría básica en sucesión para proteger a tu familia.') :-
    Perfil.tiene_testamento == false.

% --- Reglas adicionales (sin usar Perfil directamente) ---
recommend(_Perfil, 'Automatiza tu ahorro: programa una transferencia automática el día de pago.') :-
    true.

recommend(_Perfil, 'Evita compras impulsivas: usa la regla de las 24 horas para gastos no esenciales.') :-
    true.

recommend(_Perfil, 'Construye historial: mantén utilización de crédito <30% y pagos puntuales.') :-
    true.

recommend(_Perfil, 'Haz revisión mensual del presupuesto y trimestral de metas.') :-
    true.

recommend(Perfil, 'Prioriza eliminar deudas de alto interés antes de invertir agresivamente.') :-
    Perfil.tasa_interes_apr > 0.

recommend(_Perfil, 'Si recibes un ingreso extra (bono/devolución), destina una parte al fondo de emergencia o a deuda.') :-
    true.

%% --------- Agregador ---------
recomendaciones(Perfil, RecsUnicos) :-
    findall(R, recommend(Perfil, R), Recs),
    sort(Recs, RecsUnicos).

%% --------- Ejemplo de uso ---------
ejemplo_perfil(_{
    ingreso: 15000,
    gasto_total: 16500,
    ahorro_mensual: 800,
    meses_fondo: 0.5,
    vivienda: 6000,
    alimentacion: 5800,
    transporte: 3500,
    deudas_total: 5200,
    cc_pago_minimo: true,
    tasa_interes_apr: 42.0,
    metas: [meta('fondo_emergencia',6), meta('auto',24)],
    jubilacion_definida: false,
    nivel_conocimiento: basic,
    tiene_seguro_salud: false,
    tiene_seguro_vida: false,
    dependientes: true,
    posee_auto: true,
    tiene_seguro_auto: false,
    gasto_medico_ratio: 0.18,
    tiene_testamento: false,
    registra_gastos: false

}).
%% =========================
%% MODO INTERACTIVO (ejemplo)
%% =========================

run_asistente :-
    writeln('--- Asistente de Planificación Financiera ---'),

    % Pedir datos al usuario
    write('Ingreso mensual neto: '), read(Ingreso),
    write('Gasto mensual total: '), read(GastoTotal),
    write('Ahorro mensual: '), read(Ahorro),
    write('Meses cubiertos por fondo de emergencia: '), read(MesesFondo),
    write('Gasto mensual en vivienda: '), read(Vivienda),
    write('Gasto mensual en alimentacion: '), read(Alimentacion),
    write('Gasto mensual en transporte: '), read(Transporte),
    write('Pago mensual de deudas: '), read(DeudaTotal),
    write('¿Paga solo el mínimo en TDC? (true/false): '), read(Minimo),
    write('APR promedio de sus deudas (%): '), read(APR),
    write('¿Tiene metas financieras? (ej: [meta(casa,24), meta(jubilacion,120)] o []): '), read(Metas),
    write('¿Ha definido aporte a jubilación? (true/false): '), read(Jub),
    write('Nivel de conocimiento financiero (basic|intermediate|advanced): '), read(Nivel),
    write('¿Tiene seguro de salud? (true/false): '), read(Salud),
    write('¿Tiene seguro de vida? (true/false): '), read(Vida),
    write('¿Tiene dependientes? (true/false): '), read(Dep),
    write('¿Posee auto? (true/false): '), read(Auto),
    write('¿Tiene seguro de auto? (true/false): '), read(SegAuto),
    write('Gasto medico / ingreso (ej: 0.10 para 10%): '), read(RatioMed),
    write('¿Tiene testamento? (true/false): '), read(Testamento),
    write('¿Registra sus gastos? (true/false): '), read(Registra),

    % Crear el dict Perfil
    Perfil = _{
        ingreso: Ingreso,
        gasto_total: GastoTotal,
        ahorro_mensual: Ahorro,
        meses_fondo: MesesFondo,
        vivienda: Vivienda,
        alimentacion: Alimentacion,
        transporte: Transporte,
        deudas_total: DeudaTotal,
        cc_pago_minimo: Minimo,
        tasa_interes_apr: APR,
        metas: Metas,
        jubilacion_definida: Jub,
        nivel_conocimiento: Nivel,
        tiene_seguro_salud: Salud,
        tiene_seguro_vida: Vida,
        dependientes: Dep,
        posee_auto: Auto,
        tiene_seguro_auto: SegAuto,
        gasto_medico_ratio: RatioMed,
        tiene_testamento: Testamento,
        registra_gastos: Registra
    },

    % Obtener recomendaciones
    recomendaciones(Perfil, Recs),
    writeln('\n--- Recomendaciones ---'),
    forall(member(R, Recs), (writeln('- '), writeln(R))).

