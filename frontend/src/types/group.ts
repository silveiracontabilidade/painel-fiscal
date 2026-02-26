export interface GroupCoordinator {
  id: number;
  username: string;
  email?: string;
}

export interface Group {
  id: number;
  nome: string;
  coordenador?: GroupCoordinator | null;
}
