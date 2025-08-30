const ACCESS_TOKEN = "access_token";

export function getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN);
}

export function setAccessToken({ access }) {
    if (typeof access === 'string') localStorage.setItem(ACCESS_TOKEN, access);
}

export function clearAccessToken() {
    localStorage.removeItem(ACCESS_TOKEN);
}