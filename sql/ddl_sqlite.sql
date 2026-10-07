-- DDL generado automáticamente por src/load/sql.py (sqlite)

CREATE TABLE gold_dim_edad (
	cod_edad TEXT NOT NULL, 
	etiqueta TEXT, 
	edad_min TEXT, 
	edad_max TEXT, 
	tipo TEXT, 
	grupo_funcional TEXT, 
	orden TEXT, 
	observacion TEXT, 
	PRIMARY KEY (cod_edad)
);

CREATE TABLE gold_dim_escenario (
	cod_escenario TEXT NOT NULL, 
	nombre_escenario TEXT, 
	familia TEXT, 
	supuesto_fecundidad TEXT, 
	supuesto_esperanza_vida TEXT, 
	supuesto_migracion TEXT, 
	orden BIGINT, 
	etiqueta_kostat TEXT, 
	PRIMARY KEY (cod_escenario)
);

CREATE TABLE gold_dim_fuente (
	fuente TEXT NOT NULL, 
	dataset TEXT NOT NULL, 
	tbl_id TEXT, 
	rol TEXT, 
	url TEXT, 
	fecha_extraccion TEXT, 
	filas TEXT, 
	archivo_crudo TEXT, 
	version TEXT, 
	PRIMARY KEY (fuente, dataset)
);

CREATE TABLE gold_dim_indicador (
	cod_indicador TEXT NOT NULL, 
	nombre TEXT, 
	categoria TEXT, 
	definicion TEXT, 
	formula TEXT, 
	unidad TEXT, 
	frecuencia_original TEXT, 
	fuente_maestra TEXT, 
	fuente_contraste TEXT, 
	es_derivado TEXT, 
	aditivo TEXT, 
	rango_min TEXT, 
	rango_max TEXT, 
	decimales TEXT, 
	PRIMARY KEY (cod_indicador)
);

CREATE TABLE gold_dim_sexo (
	cod_sexo TEXT NOT NULL, 
	nombre TEXT, 
	orden BIGINT, 
	PRIMARY KEY (cod_sexo)
);

CREATE TABLE gold_dim_supuesto (
	cod_supuesto TEXT NOT NULL, 
	nombre TEXT, 
	descripcion TEXT, 
	PRIMARY KEY (cod_supuesto)
);

CREATE TABLE gold_dim_territorio (
	cod_territorio TEXT NOT NULL, 
	nombre_es TEXT, 
	nombre_en TEXT, 
	nombre_ko TEXT, 
	tipo TEXT, 
	region_macro TEXT, 
	cod_oecd_tl3 TEXT, 
	iso3 TEXT, 
	vigente_desde TEXT, 
	orden TEXT, 
	observacion TEXT, 
	PRIMARY KEY (cod_territorio)
);

CREATE TABLE gold_dim_tiempo (
	anio BIGINT NOT NULL, 
	decada TEXT, 
	quinquenio TEXT, 
	periodo TEXT, 
	en_ventana_analisis BOOLEAN, 
	horizonte TEXT, 
	PRIMARY KEY (anio)
);

CREATE TABLE gold_dim_tipo_dato (
	tipo_dato TEXT NOT NULL, 
	descripcion TEXT, 
	orden BIGINT, 
	PRIMARY KEY (tipo_dato)
);

CREATE TABLE gold_dataset_nacional_anual (
	anio BIGINT NOT NULL, 
	cod_territorio TEXT NOT NULL, 
	"CRECIMIENTO_NATURAL" FLOAT, 
	"DEFUNCIONES" FLOAT, 
	"DEP_JUVENIL" FLOAT, 
	"DEP_TOTAL" FLOAT, 
	"DEP_VEJEZ" FLOAT, 
	"ESPERANZA_VIDA" FLOAT, 
	"IND_ENVEJECIMIENTO" FLOAT, 
	"IND_REEMPLAZO_LABORAL" FLOAT, 
	"MATRIMONIOS" FLOAT, 
	"MORTALIDAD_INFANTIL" FLOAT, 
	"NACIMIENTOS" FLOAT, 
	"OCUPADOS" FLOAT, 
	"POB_15MAS" FLOAT, 
	"POB_ACTIVA" FLOAT, 
	"POB_EXTRANJERA" FLOAT, 
	"PROP_0_14" FLOAT, 
	"PROP_15_64" FLOAT, 
	"PROP_65MAS" FLOAT, 
	"PROP_80MAS" FLOAT, 
	"PROP_EXTRANJEROS" FLOAT, 
	"RATIO_SOPORTE" FLOAT, 
	"TASA_BRUTA_NATALIDAD" FLOAT, 
	"TASA_DESEMPLEO" FLOAT, 
	"TASA_EMPLEO" FLOAT, 
	"TASA_PARTICIPACION" FLOAT, 
	"TFR" FLOAT, 
	"POB_0_14" FLOAT, 
	"POB_15_64" FLOAT, 
	"POB_65MAS" FLOAT, 
	"POB_TOTAL" FLOAT, 
	tipo_dato_poblacion TEXT, 
	"FLP_A" FLOAT, 
	"FLP_B" FLOAT, 
	"FLP_C" FLOAT, 
	"FLP_D" FLOAT, 
	"PIB_HORA" FLOAT, 
	periodo TEXT, 
	PRIMARY KEY (anio, cod_territorio), 
	FOREIGN KEY(anio) REFERENCES gold_dim_tiempo (anio), 
	FOREIGN KEY(cod_territorio) REFERENCES gold_dim_territorio (cod_territorio)
);

CREATE TABLE gold_dataset_regional_anual (
	anio BIGINT NOT NULL, 
	cod_territorio TEXT NOT NULL, 
	"CRECIMIENTO_NATURAL" FLOAT, 
	"DEFUNCIONES" FLOAT, 
	"DEP_JUVENIL" FLOAT, 
	"DEP_TOTAL" FLOAT, 
	"DEP_VEJEZ" FLOAT, 
	"IND_ENVEJECIMIENTO" FLOAT, 
	"IND_REEMPLAZO_LABORAL" FLOAT, 
	"MATRIMONIOS" FLOAT, 
	"NACIMIENTOS" FLOAT, 
	"OCUPADOS" FLOAT, 
	"POB_15MAS" FLOAT, 
	"POB_ACTIVA" FLOAT, 
	"POB_EXTRANJERA" FLOAT, 
	"PROP_0_14" FLOAT, 
	"PROP_15_64" FLOAT, 
	"PROP_65MAS" FLOAT, 
	"PROP_80MAS" FLOAT, 
	"PROP_EXTRANJEROS" FLOAT, 
	"RATIO_SOPORTE" FLOAT, 
	"TASA_BRUTA_NATALIDAD" FLOAT, 
	"TASA_DESEMPLEO" FLOAT, 
	"TASA_EMPLEO" FLOAT, 
	"TASA_PARTICIPACION" FLOAT, 
	"TFR" FLOAT, 
	"POB_0_14" FLOAT, 
	"POB_15_64" FLOAT, 
	"POB_65MAS" FLOAT, 
	"POB_TOTAL" FLOAT, 
	tipo_dato_poblacion TEXT, 
	periodo TEXT, 
	PRIMARY KEY (anio, cod_territorio), 
	FOREIGN KEY(anio) REFERENCES gold_dim_tiempo (anio), 
	FOREIGN KEY(cod_territorio) REFERENCES gold_dim_territorio (cod_territorio)
);

CREATE TABLE gold_fact_comparacion_internacional (
	anio BIGINT NOT NULL, 
	cod_territorio TEXT NOT NULL, 
	cod_sexo TEXT NOT NULL, 
	cod_edad TEXT NOT NULL, 
	cod_indicador TEXT NOT NULL, 
	valor FLOAT, 
	fuente TEXT NOT NULL, 
	dataset TEXT, 
	tabla_fuente TEXT, 
	tipo_dato TEXT, 
	PRIMARY KEY (anio, cod_territorio, cod_sexo, cod_edad, cod_indicador, fuente), 
	FOREIGN KEY(anio) REFERENCES gold_dim_tiempo (anio), 
	FOREIGN KEY(cod_territorio) REFERENCES gold_dim_territorio (cod_territorio), 
	FOREIGN KEY(cod_sexo) REFERENCES gold_dim_sexo (cod_sexo), 
	FOREIGN KEY(cod_edad) REFERENCES gold_dim_edad (cod_edad), 
	FOREIGN KEY(cod_indicador) REFERENCES gold_dim_indicador (cod_indicador), 
	FOREIGN KEY(tipo_dato) REFERENCES gold_dim_tipo_dato (tipo_dato)
);

CREATE TABLE gold_fact_conciliacion (
	anio BIGINT, 
	cod_territorio TEXT, 
	cod_sexo TEXT, 
	cod_edad TEXT, 
	cod_indicador TEXT, 
	valor_maestra FLOAT, 
	fuente_maestra TEXT, 
	dataset_maestra TEXT, 
	valor_contraste FLOAT, 
	fuente_contraste TEXT, 
	dataset_contraste TEXT, 
	dif_abs FLOAT, 
	dif_pct FLOAT, 
	comparable BOOLEAN, 
	nota TEXT, 
	dentro_tolerancia BOOLEAN, 
	tipo_comparacion TEXT
);

CREATE TABLE gold_fact_escenarios_sensibilidad (
	cod_supuesto TEXT NOT NULL, 
	variante TEXT NOT NULL, 
	es_base BOOLEAN, 
	fuerza_laboral_2025 FLOAT, 
	fuerza_laboral_2050 FLOAT, 
	var_2050_pct FLOAT, 
	var_2072_pct FLOAT, 
	tipo_dato TEXT, 
	PRIMARY KEY (cod_supuesto, variante), 
	FOREIGN KEY(cod_supuesto) REFERENCES gold_dim_supuesto (cod_supuesto), 
	FOREIGN KEY(tipo_dato) REFERENCES gold_dim_tipo_dato (tipo_dato)
);

CREATE TABLE gold_fact_fuerza_laboral_escenario (
	anio BIGINT NOT NULL, 
	cod_escenario TEXT NOT NULL, 
	cod_sexo TEXT NOT NULL, 
	cod_edad TEXT NOT NULL, 
	poblacion_proyectada FLOAT, 
	tasa_participacion FLOAT, 
	cod_supuesto TEXT NOT NULL, 
	factor_cobertura FLOAT, 
	fuerza_laboral_potencial FLOAT, 
	tipo_dato TEXT, 
	fuerza_laboral_total_anio FLOAT, 
	fuerza_laboral_total_base FLOAT, 
	indice_base_2025 FLOAT, 
	PRIMARY KEY (anio, cod_escenario, cod_sexo, cod_edad, cod_supuesto), 
	FOREIGN KEY(anio) REFERENCES gold_dim_tiempo (anio), 
	FOREIGN KEY(cod_escenario) REFERENCES gold_dim_escenario (cod_escenario), 
	FOREIGN KEY(cod_sexo) REFERENCES gold_dim_sexo (cod_sexo), 
	FOREIGN KEY(cod_edad) REFERENCES gold_dim_edad (cod_edad), 
	FOREIGN KEY(cod_supuesto) REFERENCES gold_dim_supuesto (cod_supuesto), 
	FOREIGN KEY(tipo_dato) REFERENCES gold_dim_tipo_dato (tipo_dato)
);

CREATE TABLE gold_fact_indicador_historico (
	anio BIGINT NOT NULL, 
	cod_territorio TEXT NOT NULL, 
	cod_sexo TEXT NOT NULL, 
	cod_edad TEXT NOT NULL, 
	cod_indicador TEXT NOT NULL, 
	valor FLOAT, 
	tipo_dato TEXT, 
	estado TEXT, 
	fuente TEXT, 
	dataset TEXT, 
	tabla_fuente TEXT, 
	version_fuente TEXT, 
	es_derivado BOOLEAN, 
	PRIMARY KEY (anio, cod_territorio, cod_sexo, cod_edad, cod_indicador), 
	FOREIGN KEY(anio) REFERENCES gold_dim_tiempo (anio), 
	FOREIGN KEY(cod_territorio) REFERENCES gold_dim_territorio (cod_territorio), 
	FOREIGN KEY(cod_sexo) REFERENCES gold_dim_sexo (cod_sexo), 
	FOREIGN KEY(cod_edad) REFERENCES gold_dim_edad (cod_edad), 
	FOREIGN KEY(cod_indicador) REFERENCES gold_dim_indicador (cod_indicador), 
	FOREIGN KEY(tipo_dato) REFERENCES gold_dim_tipo_dato (tipo_dato)
);

CREATE TABLE gold_fact_indicador_proyeccion (
	anio BIGINT NOT NULL, 
	cod_territorio TEXT NOT NULL, 
	cod_sexo TEXT NOT NULL, 
	cod_edad TEXT NOT NULL, 
	cod_indicador TEXT NOT NULL, 
	cod_escenario TEXT NOT NULL, 
	edicion_proyeccion TEXT NOT NULL, 
	valor FLOAT, 
	tipo_dato TEXT, 
	fuente TEXT, 
	dataset TEXT, 
	estado TEXT, 
	PRIMARY KEY (anio, cod_territorio, cod_sexo, cod_edad, cod_indicador, cod_escenario, edicion_proyeccion), 
	FOREIGN KEY(anio) REFERENCES gold_dim_tiempo (anio), 
	FOREIGN KEY(cod_territorio) REFERENCES gold_dim_territorio (cod_territorio), 
	FOREIGN KEY(cod_sexo) REFERENCES gold_dim_sexo (cod_sexo), 
	FOREIGN KEY(cod_edad) REFERENCES gold_dim_edad (cod_edad), 
	FOREIGN KEY(cod_indicador) REFERENCES gold_dim_indicador (cod_indicador), 
	FOREIGN KEY(cod_escenario) REFERENCES gold_dim_escenario (cod_escenario), 
	FOREIGN KEY(tipo_dato) REFERENCES gold_dim_tipo_dato (tipo_dato)
);

CREATE TABLE gold_fact_riesgo_regional (
	cod_territorio TEXT NOT NULL, 
	tfr FLOAT, 
	prop_65mas FLOAT, 
	dep_vejez FLOAT, 
	tasa_participacion FLOAT, 
	ind_reemplazo_laboral FLOAT, 
	pob_15_64_base FLOAT, 
	pob_15_64_2052 FLOAT, 
	nacimientos_2015 FLOAT, 
	nacimientos_base FLOAT, 
	var_pob_15_64_2052_pct FLOAT, 
	var_nacimientos_10a_pct FLOAT, 
	z_tfr FLOAT, 
	z_prop_65mas FLOAT, 
	z_dep_vejez FLOAT, 
	z_tasa_participacion FLOAT, 
	z_ind_reemplazo_laboral FLOAT, 
	z_var_pob_15_64_2052_pct FLOAT, 
	indice_riesgo FLOAT, 
	ranking_riesgo BIGINT, 
	nivel_riesgo TEXT, 
	anio_referencia BIGINT, 
	tipo_dato TEXT, 
	nota TEXT, 
	PRIMARY KEY (cod_territorio), 
	FOREIGN KEY(cod_territorio) REFERENCES gold_dim_territorio (cod_territorio), 
	FOREIGN KEY(tipo_dato) REFERENCES gold_dim_tipo_dato (tipo_dato)
);

CREATE TABLE gold_fact_riesgo_sensibilidad (
	esquema TEXT NOT NULL, 
	descripcion TEXT, 
	cod_territorio TEXT NOT NULL, 
	indice FLOAT, 
	ranking BIGINT, 
	en_top5 BOOLEAN, 
	tipo_dato TEXT, 
	PRIMARY KEY (esquema, cod_territorio), 
	FOREIGN KEY(cod_territorio) REFERENCES gold_dim_territorio (cod_territorio), 
	FOREIGN KEY(tipo_dato) REFERENCES gold_dim_tipo_dato (tipo_dato)
);

CREATE TABLE gold_kpi_calidad_dataset (
	dataset TEXT NOT NULL, 
	registros_evaluados BIGINT, 
	registros_validos BIGINT, 
	registros_rechazados BIGINT, 
	rechazos_trazados FLOAT, 
	tasa_validos_pct FLOAT, 
	tasa_rechazo_pct FLOAT, 
	rechazos_trazados_pct FLOAT, 
	cumple_validos BOOLEAN, 
	cumple_rechazo BOOLEAN, 
	PRIMARY KEY (dataset)
);

CREATE TABLE gold_kpi_completitud (
	nivel TEXT, 
	cod_indicador TEXT, 
	cod_territorio TEXT, 
	celdas_esperadas BIGINT, 
	celdas_observadas BIGINT, 
	celdas_con_proyeccion BIGINT, 
	anios_faltantes TEXT
);

CREATE TABLE gold_kpi_indicadores (
	codigo TEXT NOT NULL, 
	eje TEXT, 
	indicador TEXT, 
	formula TEXT, 
	fuente TEXT, 
	tipo_dato TEXT, 
	anio BIGINT, 
	valor FLOAT, 
	valor_texto TEXT, 
	unidad TEXT, 
	referencia TEXT, 
	semaforo TEXT, 
	lectura TEXT, 
	PRIMARY KEY (codigo), 
	FOREIGN KEY(tipo_dato) REFERENCES gold_dim_tipo_dato (tipo_dato), 
	FOREIGN KEY(anio) REFERENCES gold_dim_tiempo (anio)
);

CREATE TABLE gold_kpi_okr (
	objetivo_cod TEXT, 
	eje TEXT, 
	objetivo TEXT, 
	kr TEXT NOT NULL, 
	kpi TEXT, 
	meta TEXT, 
	valor TEXT, 
	cumple BOOLEAN, 
	interpretacion TEXT, 
	tabla_gold TEXT, 
	tipo_kpi TEXT, 
	formula TEXT, 
	PRIMARY KEY (kr)
);
