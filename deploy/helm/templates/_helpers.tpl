{{/*
Expand the name of the chart.
*/}}
{{- define "recipie.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "recipie.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "recipie.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "recipie.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "recipie.selectorLabels" -}}
app.kubernetes.io/name: {{ include "recipie.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Component fully qualified names.
*/}}
{{- define "recipie.backend.fullname" -}}
{{- printf "%s-backend" (include "recipie.fullname" .) }}
{{- end }}

{{- define "recipie.rustfs.fullname" -}}
{{- printf "%s-rustfs" (include "recipie.fullname" .) }}
{{- end }}

{{- define "recipie.web.fullname" -}}
{{- printf "%s-web" (include "recipie.fullname" .) }}
{{- end }}

{{- define "recipie.docs.fullname" -}}
{{- printf "%s-docs" (include "recipie.fullname" .) }}
{{- end }}

{{/*
CNPG cluster name and the read-write service it creates.
*/}}
{{- define "recipie.db.name" -}}
{{- printf "%s-db" (include "recipie.fullname" .) }}
{{- end }}

{{- define "recipie.db.rwService" -}}
{{- printf "%s-db-rw" (include "recipie.fullname" .) }}
{{- end }}

{{/*
Secret names.
*/}}
{{- define "recipie.db.appSecretName" -}}
{{- printf "%s-db-app" (include "recipie.fullname" .) }}
{{- end }}

{{- define "recipie.rustfs.secretName" -}}
{{- printf "%s-rustfs" (include "recipie.fullname" .) }}
{{- end }}

{{/*
Name of the Secret holding backend env (DATABASE_URL, S3 + app secrets).
Falls back to an externally-provided existingSecret.
*/}}
{{- define "recipie.backend.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- printf "%s-backend" (include "recipie.fullname" .) }}
{{- end }}
{{- end }}

{{/*
asyncpg DATABASE_URL pointing at the CNPG read-write service.
*/}}
{{- define "recipie.databaseUrl" -}}
{{- printf "postgresql+asyncpg://%s:%s@%s:5432/%s" .Values.cnpg.owner .Values.secrets.dbPassword (include "recipie.db.rwService" .) .Values.cnpg.database }}
{{- end }}
