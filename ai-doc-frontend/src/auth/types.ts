export interface User {
  username: string;
  password: string; // hashed? for demo we store plaintext — replace with hash in prod
  email: string;
  name?: string;
  profession?: string;
  purpose?: string;
  createdAt: string;
}
