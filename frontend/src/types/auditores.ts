export interface DctfwebPosicaoGeralItem {
  cod_folha: number;
  razao_social: string;
  cnpj_original: string;
  inicio_contrato: string | null;
  termino_contrato: string | null;
  sistema: string;
  origem: string;
  classificacao2: string;
  tipo: string;
  situacao: string;
  saldo_pagar: string | number | null;
  saldo_pagar_formatado: string;
}

export interface DctfwebUltimaAtualizacao {
  competencia: string;
  ultima_atualizacao: string | null;
}

export interface DctfwebPosicaoGeralResponse {
  competencias: string[];
  competencia_selecionada: string | null;
  ultimas_atualizacoes: DctfwebUltimaAtualizacao[];
  results: DctfwebPosicaoGeralItem[];
}
