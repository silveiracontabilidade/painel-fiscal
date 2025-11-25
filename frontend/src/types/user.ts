export interface UserAccount {
  id: number;
  username: string;
  email?: string;
  profile: 'administrador' | 'analista';
}
