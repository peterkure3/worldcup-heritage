use actix_web::{get, web, HttpResponse, Responder};
use std::sync::Mutex;
use crate::models::groups::GroupsData;

pub struct GroupsState {
    pub groups: Mutex<GroupsData>,
}

#[get("/api/groups")]
pub async fn get_groups(state: web::Data<GroupsState>) -> impl Responder {
    let groups = state.groups.lock().unwrap();
    HttpResponse::Ok().json(groups.clone())
}
