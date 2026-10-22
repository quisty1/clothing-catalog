export function GET(){return Response.json({status:'ok',instance:process.env.HOSTNAME || 'local'});}
